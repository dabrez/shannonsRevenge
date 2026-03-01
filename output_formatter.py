import json
import csv
from typing import List, Dict
from datetime import datetime
from detector import ClaudeDetection


class OutputFormatter:
    """Handles output formatting for scan results."""

    @staticmethod
    def to_json(detections: List[ClaudeDetection], filepath: str = None) -> str:
        """
        Format detections as JSON.

        Args:
            detections: List of ClaudeDetection objects
            filepath: Optional filepath to write JSON to

        Returns:
            JSON string
        """
        data = {
            "scan_timestamp": datetime.utcnow().isoformat(),
            "total_detections": len(detections),
            "detections": [
                {
                    "repository": f"{d.repo_owner}/{d.repo_name}",
                    "commit_sha": d.commit_sha,
                    "commit_url": d.commit_url,
                    "author": d.author,
                    "author_email": d.author_email,
                    "commit_date": d.commit_date,
                    "commit_message": d.commit_message,
                    "detection_type": d.detection_type,
                    "evidence": d.evidence,
                    "files_modified": d.files_modified,
                    "copilot_enabled": d.copilot_enabled,
                    "additional_metadata": d.additional_metadata
                }
                for d in detections
            ]
        }

        json_str = json.dumps(data, indent=2)

        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)

        return json_str

    @staticmethod
    def to_csv(detections: List[ClaudeDetection], filepath: str):
        """
        Format detections as CSV.

        Args:
            detections: List of ClaudeDetection objects
            filepath: Filepath to write CSV to
        """
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Repository",
                "Commit SHA",
                "Commit URL",
                "Author",
                "Author Email",
                "Commit Date",
                "Detection Type",
                "Evidence",
                "Copilot Enabled",
                "Files Modified",
                "Commit Message (first 100 chars)"
            ])

            for d in detections:
                writer.writerow([
                    f"{d.repo_owner}/{d.repo_name}",
                    d.commit_sha,
                    d.commit_url,
                    d.author,
                    d.author_email,
                    d.commit_date,
                    d.detection_type,
                    d.evidence,
                    "Yes" if d.copilot_enabled else "No",
                    "; ".join(d.files_modified),
                    d.commit_message[:100] + "..." if len(d.commit_message) > 100 else d.commit_message
                ])

    @staticmethod
    def to_text_report(detections: List[ClaudeDetection], summary: Dict, filepath: str = None) -> str:
        """
        Format detections as human-readable text report.

        Args:
            detections: List of ClaudeDetection objects
            summary: Summary statistics dictionary
            filepath: Optional filepath to write report to

        Returns:
            Text report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("SHANNON REVENGE - CLAUDE SUPPLY CHAIN DETECTION REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        lines.append("")

        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Detections: {summary['total_detections']}")
        lines.append(f"Repositories Affected: {summary['repositories_affected']}")
        if summary.get('copilot_enabled_detections', 0) > 0:
            lines.append(f"Detections with GitHub Copilot Enabled: {summary['copilot_enabled_detections']}")
            lines.append(f"Repositories with Copilot: {summary['repositories_with_copilot']}")
        lines.append("")

        lines.append("Detections by Type:")
        for det_type, count in summary['by_detection_type'].items():
            lines.append(f"  - {det_type}: {count}")
        lines.append("")

        lines.append("Detections by Repository:")
        for repo, count in summary['by_repository'].items():
            lines.append(f"  - {repo}: {count}")
        lines.append("")

        lines.append("=" * 80)
        lines.append("DETAILED DETECTIONS")
        lines.append("=" * 80)
        lines.append("")

        for i, d in enumerate(detections, 1):
            lines.append(f"[{i}] {d.repo_owner}/{d.repo_name}")
            lines.append(f"    Commit: {d.commit_sha[:8]}")
            lines.append(f"    URL: {d.commit_url}")
            lines.append(f"    Author: {d.author} <{d.author_email}>")
            lines.append(f"    Date: {d.commit_date}")
            lines.append(f"    Detection Type: {d.detection_type}")
            lines.append(f"    Evidence: {d.evidence}")
            if d.copilot_enabled:
                lines.append(f"    GitHub Copilot: ENABLED")
            if d.files_modified:
                lines.append(f"    Files Modified ({len(d.files_modified)}):")
                for f in d.files_modified[:5]:
                    lines.append(f"      - {f}")
                if len(d.files_modified) > 5:
                    lines.append(f"      ... and {len(d.files_modified) - 5} more")
            lines.append(f"    Commit Message:")
            for line in d.commit_message.split('\n')[:3]:
                lines.append(f"      {line}")
            if len(d.commit_message.split('\n')) > 3:
                lines.append("      ...")
            lines.append("")

        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        report = "\n".join(lines)

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)

        return report

    @staticmethod
    def print_summary(summary: Dict):
        """
        Print a brief summary to console.

        Args:
            summary: Summary statistics dictionary
        """
        print("\n" + "=" * 60)
        print("SCAN SUMMARY")
        print("=" * 60)
        print(f"Total Detections: {summary['total_detections']}")
        print(f"Repositories Affected: {summary['repositories_affected']}")
        if summary.get('copilot_enabled_detections', 0) > 0:
            print(f"Detections with GitHub Copilot: {summary['copilot_enabled_detections']}")
            print(f"Repositories with Copilot: {summary['repositories_with_copilot']}")
        print("\nDetections by Type:")
        for det_type, count in summary['by_detection_type'].items():
            print(f"  - {det_type}: {count}")
        print("=" * 60 + "\n")
