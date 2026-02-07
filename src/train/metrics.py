import torch


@torch.no_grad()
def topk_accuracy(logits: torch.Tensor, targets: torch.Tensor, k: int = 1) -> float:
    """
    logits: (B, C)
    targets: (B,)
    """
    topk = torch.topk(logits, k=k, dim=1).indices  # (B, k)
    correct = topk.eq(targets.view(-1, 1)).any(dim=1).float().mean().item()
    return correct
