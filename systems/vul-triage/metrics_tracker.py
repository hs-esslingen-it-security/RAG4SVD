from datetime import datetime
from pathlib import Path

class VulnerabilityMetricsTracker:
    """Vulnerability detection evaluation metrics tracker."""

    def __init__(self, output_file="metrics_log.txt"):
        """
        Initialize the tracker.

        :param output_file: Output file path (TXT format)
        """
        self.output_file = Path(output_file)
        self.reset_metrics()

    def reset_metrics(self):
        """Reset all evaluation metrics."""
        self.metrics = {
            "p_c": 0,
            "p_v": 0,
            "p_b": 0,
            "p_r": 0,
            "e": 0,
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "tp": 0,
            "total_pairs": 0,
            "total_samples": 0
        }

    def update_pair_metrics(self, pred_i, pred_j, true_i, true_j):
        """
        Update evaluation metrics for a pair of samples.

        :param pred_i: Predicted label of sample i
        :param pred_j: Predicted label of sample j
        :param true_i: Ground-truth label of sample i
        :param true_j: Ground-truth label of sample j
        """
        if pred_i == true_i and pred_j == true_j:
            self.metrics["p_c"] += 1

        if pred_i == 1 and pred_j == 1:
            self.metrics["p_v"] += 1

        if pred_i == 0 and pred_j == 0:
            self.metrics["p_b"] += 1

        if pred_i != true_i and pred_j != true_j:
            self.metrics["p_r"] += 1

        if pred_i != true_i or pred_j != true_j:
            self.metrics["e"] += 1

        self._update_single_sample(pred_i, true_i)
        self._update_single_sample(pred_j, true_j)

        self.metrics["total_pairs"] += 1
        self.metrics["total_samples"] += 2

        self._save_current_state()

    def _update_single_sample(self, pred, true):
        """Update TP/FP/TN/FN metrics for a single sample."""
        if true == 1 and pred == 1:
            self.metrics["tp"] += 1
        elif true == 0 and pred == 1:
            self.metrics["fp"] += 1
        elif true == 0 and pred == 0:
            self.metrics["tn"] += 1
        elif true == 1 and pred == 0:
            self.metrics["fn"] += 1

    def _save_current_state(self):
        """Save the current evaluation metrics to a TXT file (overwrite mode)."""
        tp = self.metrics["tp"]
        fp = self.metrics["fp"]
        tn = self.metrics["tn"]
        fn = self.metrics["fn"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

        content = (
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"\n"
            f"[Progress]\n"
            f"Processed Pairs: {self.metrics['total_pairs']}\n"
            f"Processed Samples: {self.metrics['total_samples']}\n"
            f"\n"
            f"[Pairwise Evaluation Metrics]\n"
            f"P-C: {self.metrics['p_c']}\n"
            f"P-V: {self.metrics['p_v']}\n"
            f"P-B: {self.metrics['p_b']}\n"
            f"P-R: {self.metrics['p_r']}\n"
            f"E:   {self.metrics['e']}\n"
            f"\n"
            f"[Single-Sample Evaluation Metrics]\n"
            f"TP: {self.metrics['tp']}, FP: {self.metrics['fp']}, TN: {self.metrics['tn']}, FN: {self.metrics['fn']}\n"
            f"\n"
            f"[Derived Metrics]\n"
            f"Precision: {precision:.4f}\n"
            f"Recall:    {recall:.4f}\n"
            f"FPR:       {fpr:.4f}\n"
        )

        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(content)
    
    def print_summary(self, mode="unknown"):
        """Print the final evaluation summary."""
        print(f"\n{'=' * 50}")
        print(f"Evaluation Metrics Summary (Mode: {mode})")
        print(f"{'=' * 50}")

        print(f"\n[Pairwise Evaluation Metrics]")
        print(
            f"P-C (Pair Correctness): {self.metrics['p_c']}/{self.metrics['total_pairs']} ({self.metrics['p_c'] / max(self.metrics['total_pairs'], 1):.4f})")
        print(
            f"P-V (Pair Vulnerable):  {self.metrics['p_v']}/{self.metrics['total_pairs']} ({self.metrics['p_v'] / max(self.metrics['total_pairs'], 1):.4f})")
        print(
            f"P-B (Pair Benign):      {self.metrics['p_b']}/{self.metrics['total_pairs']} ({self.metrics['p_b'] / max(self.metrics['total_pairs'], 1):.4f})")
        print(
            f"P-R (Pair Reversed):    {self.metrics['p_r']}/{self.metrics['total_pairs']} ({self.metrics['p_r'] / max(self.metrics['total_pairs'], 1):.4f})")
        print(
            f"E (Error Rate):         {self.metrics['e']}/{self.metrics['total_pairs']} ({self.metrics['e'] / max(self.metrics['total_pairs'], 1):.4f})")

        print(f"\n[Single-Sample Evaluation Metrics]")
        tp = self.metrics["tp"]
        fp = self.metrics["fp"]
        tn = self.metrics["tn"]
        fn = self.metrics["fn"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

        print(f"TP: {tp}, FP: {fp}, TN: {tn}, FN: {fn}")
        print(f"\nP (Precision): {precision:.4f}")
        print(f"R (Recall):    {recall:.4f}")
        print(f"FPR:           {fpr:.4f}")
        print(f"\nTotal Samples: {self.metrics['total_samples']}")
        print(f"Total Pairs:   {self.metrics['total_pairs']}")
        print(f"{'=' * 50}\n")


if __name__ == "__main__":
    tracker = VulnerabilityMetricsTracker("test_metrics.txt")
    tracker.update_pair_metrics(1, 0, 1, 0)
    tracker.update_pair_metrics(1, 1, 1, 0)
    tracker.update_pair_metrics(1, 0, 1, 0)
    tracker.update_pair_metrics(1, 1, 1, 0)
    tracker.print_summary(mode="test")
