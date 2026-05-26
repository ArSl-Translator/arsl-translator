#include <jni.h>
#include <android/log.h>

#include "llama.h"

#include <algorithm>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

#define LOG_TAG "ArslLlama"
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

struct ArslModel {
    llama_model * model = nullptr;
    const llama_vocab * vocab = nullptr;
    std::mutex mutex;
};

static std::once_flag g_backend_once;

static std::string jstring_to_string(JNIEnv * env, jstring value) {
    if (value == nullptr) {
        return "";
    }
    const char * chars = env->GetStringUTFChars(value, nullptr);
    if (chars == nullptr) {
        return "";
    }
    std::string result(chars);
    env->ReleaseStringUTFChars(value, chars);
    return result;
}

static void throw_java(JNIEnv * env, const char * message) {
    jclass clazz = env->FindClass("java/lang/IllegalStateException");
    if (clazz != nullptr) {
        env->ThrowNew(clazz, message);
    }
}

static std::vector<llama_token> tokenize_prompt(const llama_vocab * vocab, const std::string & prompt) {
    int n_prompt = -llama_tokenize(
        vocab,
        prompt.c_str(),
        static_cast<int32_t>(prompt.size()),
        nullptr,
        0,
        true,
        true
    );

    if (n_prompt <= 0) {
        throw std::runtime_error("Failed to size prompt tokens");
    }

    std::vector<llama_token> tokens(n_prompt);
    int actual = llama_tokenize(
        vocab,
        prompt.c_str(),
        static_cast<int32_t>(prompt.size()),
        tokens.data(),
        static_cast<int32_t>(tokens.size()),
        true,
        true
    );

    if (actual < 0) {
        throw std::runtime_error("Failed to tokenize prompt");
    }

    tokens.resize(actual);
    return tokens;
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_healthcare_offlinechat_ai_LlamaBridge_loadModel(
    JNIEnv * env,
    jobject,
    jstring model_path
) {
    try {
        std::call_once(g_backend_once, [] {
            ggml_backend_load_all();
        });

        std::string path = jstring_to_string(env, model_path);
        if (path.empty()) {
            throw std::runtime_error("Model path is empty");
        }

        llama_model_params model_params = llama_model_default_params();
        model_params.n_gpu_layers = 0;

        llama_model * model = llama_model_load_from_file(path.c_str(), model_params);
        if (model == nullptr) {
            throw std::runtime_error("Could not load GGUF model");
        }

        auto * holder = new ArslModel();
        holder->model = model;
        holder->vocab = llama_model_get_vocab(model);
        return reinterpret_cast<jlong>(holder);
    } catch (const std::exception & error) {
        LOGE("loadModel failed: %s", error.what());
        throw_java(env, error.what());
        return 0;
    }
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_healthcare_offlinechat_ai_LlamaBridge_generate(
    JNIEnv * env,
    jobject,
    jlong handle,
    jstring prompt_value,
    jint max_tokens,
    jfloat temperature
) {
    auto * holder = reinterpret_cast<ArslModel *>(handle);
    if (holder == nullptr || holder->model == nullptr || holder->vocab == nullptr) {
        throw_java(env, "Offline model is not loaded");
        return env->NewStringUTF("");
    }

    std::lock_guard<std::mutex> lock(holder->mutex);

    llama_context * ctx = nullptr;
    llama_sampler * sampler = nullptr;

    try {
        std::string prompt = jstring_to_string(env, prompt_value);
        auto prompt_tokens = tokenize_prompt(holder->vocab, prompt);
        int n_predict = std::max(1, static_cast<int>(max_tokens));
        int n_ctx = std::min(2048, static_cast<int>(prompt_tokens.size()) + n_predict + 32);
        int n_batch = std::min(512, std::max(1, static_cast<int>(prompt_tokens.size())));

        llama_context_params ctx_params = llama_context_default_params();
        ctx_params.n_ctx = n_ctx;
        ctx_params.n_batch = n_batch;
        ctx_params.no_perf = true;

        ctx = llama_init_from_model(holder->model, ctx_params);
        if (ctx == nullptr) {
            throw std::runtime_error("Could not create llama context");
        }

        auto sampler_params = llama_sampler_chain_default_params();
        sampler_params.no_perf = true;
        sampler = llama_sampler_chain_init(sampler_params);

        if (temperature <= 0.0f) {
            llama_sampler_chain_add(sampler, llama_sampler_init_greedy());
        } else {
            llama_sampler_chain_add(sampler, llama_sampler_init_top_k(40));
            llama_sampler_chain_add(sampler, llama_sampler_init_top_p(0.9f, 1));
            llama_sampler_chain_add(sampler, llama_sampler_init_temp(temperature));
            llama_sampler_chain_add(sampler, llama_sampler_init_dist(LLAMA_DEFAULT_SEED));
        }

        llama_batch batch = llama_batch_get_one(prompt_tokens.data(), static_cast<int32_t>(prompt_tokens.size()));
        std::string output;
        int n_pos = 0;

        for (int i = 0; i < n_predict; ++i) {
            if (llama_decode(ctx, batch) != 0) {
                throw std::runtime_error("llama_decode failed");
            }

            n_pos += batch.n_tokens;
            llama_token token = llama_sampler_sample(sampler, ctx, -1);
            if (llama_vocab_is_eog(holder->vocab, token)) {
                break;
            }

            char piece[256];
            int piece_size = llama_token_to_piece(holder->vocab, token, piece, sizeof(piece), 0, true);
            if (piece_size > 0) {
                output.append(piece, piece_size);
            }

            batch = llama_batch_get_one(&token, 1);
        }

        llama_sampler_free(sampler);
        llama_free(ctx);
        return env->NewStringUTF(output.c_str());
    } catch (const std::exception & error) {
        LOGE("generate failed: %s", error.what());
        if (sampler != nullptr) {
            llama_sampler_free(sampler);
        }
        if (ctx != nullptr) {
            llama_free(ctx);
        }
        throw_java(env, error.what());
        return env->NewStringUTF("");
    }
}

extern "C" JNIEXPORT void JNICALL
Java_com_healthcare_offlinechat_ai_LlamaBridge_freeModel(
    JNIEnv *,
    jobject,
    jlong handle
) {
    auto * holder = reinterpret_cast<ArslModel *>(handle);
    if (holder == nullptr) {
        return;
    }
    if (holder->model != nullptr) {
        llama_model_free(holder->model);
        holder->model = nullptr;
    }
    delete holder;
}
