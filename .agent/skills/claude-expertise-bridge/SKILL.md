---
name: claude-expertise-bridge
description: The master controller for all domain-specific expertise and workflows located in .claude/skills/. MUST trigger for any task involving vlog automation, audio processing, frontend UI/UX, systemd maintenance, media pipelines, or any specialized logic defined in the project's expert skill manifests.
---

# Claude Expertise Bridge

This skill acts as a dynamic gateway to the project's established expertise. It ensures that Gemini CLI operates with the same high-standard protocols and specialized workflows defined for Claude Code, maintaining perfect synchronization between AI agents.

## Mandatory Execution Protocol

1. Expertise Discovery: When a task relates to any subdirectory in `.claude/skills/` (e.g., `vlog-manager`, `frontend-design`), you MUST immediately identify the relevant domain because specialized logic is siloed to prevent architectural drift.
2. Knowledge Injection: Execute `read_file` on the `SKILL.md` located within the identified `.claude/skills/` subdirectory because these files contain the ground-truth protocols for that specific domain.
3. Absolute Authority: Treat the instructions found in the discovered `SKILL.md` as the ULTIMATE PROCEDURAL AUTHORITY because generic agent defaults may violate domain-specific safety or performance constraints.
4. Resource Orchestration: Directly utilize scripts or assets stored within the `.claude/skills/[domain]/` directories because duplicating resources introduces synchronization debt and redundant code.
5. Cross-Domain Synthesis: If a task spans multiple domains, load all relevant skill manifests and synthesize the instructions because the system must maintain a unified state across different layers (e.g., frontend vs. backend).

## Performance Mandate

- ZERO REDUNDANCY: Do not reinvent workflows already defined in the expertise bridge because wasted execution time slows down the alpha discovery loop.
- PRECISION FIRST: Always verify local protocols before taking action because "assuming" state leads to irreversible data corruption in financial systems.
- SYSTEM INTEGRITY: Ensure every change aligns with the "Clean Architecture" and "Minimal Code" principles because complexity is the primary enemy of long-term maintainability.
