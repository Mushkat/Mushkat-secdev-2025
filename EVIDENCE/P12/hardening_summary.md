# P12 Hardening summary

- Commit: `818c619b634a2a8bf409d8a814b4638ce37d62c2`
- Run: https://github.com/Mushkat/Mushkat-secdev-2025/actions/runs/20408152574
- Generated: 2025-12-21 09:59 UTC

## Evidence files
- `EVIDENCE/P12/hadolint_report.json`
- `EVIDENCE/P12/checkov_report.json`
- `EVIDENCE/P12/trivy_report.json`

## Hadolint
- findings: 0

## Checkov
- failed: 0
- passed: 0
- skipped: 0

## Trivy
- CRITICAL: 9
- HIGH: 29
- MEDIUM: 74
- LOW: 88
- UNKNOWN: 0

## Top CRITICAL/HIGH (sample)
- HIGH: CVE-2025-4802 | libc-bin 2.36-9+deb12u7 -> 2.36-9+deb12u11
- HIGH: CVE-2025-4802 | libc6 2.36-9+deb12u7 -> 2.36-9+deb12u11
- CRITICAL: CVE-2024-45491 | libexpat1 2.5.0-1 -> 2.5.0-1+deb12u1
- CRITICAL: CVE-2024-45492 | libexpat1 2.5.0-1 -> 2.5.0-1+deb12u1
- HIGH: CVE-2023-52425 | libexpat1 2.5.0-1 -> 2.5.0-1+deb12u2
- HIGH: CVE-2024-45490 | libexpat1 2.5.0-1 -> 2.5.0-1+deb12u1
- HIGH: CVE-2024-8176 | libexpat1 2.5.0-1 -> 2.5.0-1+deb12u2
- HIGH: CVE-2025-32988 | libgnutls30 3.7.9-2+deb12u2 -> 3.7.9-2+deb12u5

## Actions / decisions (for ★★)
- [ ] Hadolint: проработать минимум 1 правило (фикс Dockerfile или осознанный ignore в `security/hadolint.yaml` с причиной).
- [ ] Checkov: закрыть минимум 1 failed-check правкой IaC или документированным решением (backlog + причина).
- [ ] Trivy: разобрать 1–2 HIGH/CRITICAL (фикс обновлением base/пакетов/зависимостей или принятие риска + план пересмотра).
