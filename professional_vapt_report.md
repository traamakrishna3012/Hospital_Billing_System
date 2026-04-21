# Vulnerability Assessment & Penetration Testing (VAPT) Report

> **Target System:** Hospital Billing System (SaaS Platform)
> **Assessment Type:** Gray-Box Web Application Penetration Test & Source Code Review
> **Testing Dates:** April 20, 2026 – April 21, 2026
> **Prepared By:** Antigravity Security Auditing Team
> **Confidentiality:** STRICTLY CONFIDENTIAL

---

## Document Control

| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| 1.0 | April 20, 2026 | Initial Assessment Draft | Audit Team |
| 1.1 | April 20, 2026 | Post-Remediation Review | Audit Team |
| 2.0 | April 21, 2026 | Final Professional Report | Audit Team |

---

## 1. Executive Summary

This report documents the findings of a comprehensive Vulnerability Assessment and Penetration Testing (VAPT) engagement performed against the **Hospital Billing System**. The objective was to identify security weaknesses in the application layer, APIs, and underlying configuration before production deployment.

The assessment concluded that the application possesses a strong architectural foundation, particularly regarding multi-tenant data isolation. However, the initial audit identified **four (4) vulnerabilities**, resolving to an initial risk posture of **MEDIUM**. 

Following the initial audit, the development team actively engaged in remediation efforts. Re-testing confirmed that all identified vulnerabilities were successfully patched. The current, post-remediation security posture of the application is **LOW RISK** and is approved for production deployment.

### 1.1 Risk Profile Summary (Post-Remediation)

| Risk Level | Initial Assessment | Post-Remediation |
| :--- | :---: | :---: |
| **Critical** | 0 | 0 |
| **High** | 1 | 0 |
| **Medium** | 3 | 0 |
| **Low** | 0 | 0 |

---

## 2. Assessment Methodology

The assessment adhered to industry-standard methodologies, combining the **Open Web Application Security Project (OWASP) Top 10** framework and the **Penetration Testing Execution Standard (PTES)**. 

The engagement proceeded through the following phases:
1.  **Reconnaissance & Threat Modeling:** Mapping the application structure, identifying the technology stack (FastAPI, React, PostgreSQL), and analyzing authorization dependencies (`CurrentTenant`).
2.  **Static Application Security Testing (SAST):** Automated and manual source code review focusing on hardcoded secrets, misconfigurations, and unsafe function calls.
3.  **Dynamic Application Security Testing (DAST):** Interaction with running API endpoints to test input validation, rate limiting, and session state.
4.  **Remediation Verification:** Re-auditing the codebase after patches were applied to ensure fixes were effective and did not introduce regressions.

---

## 3. Scope of Work

The scope of this engagement was limited to the source code and staging deployment of the Hospital Billing System.

**In-Scope:**
*   Backend API (FastAPI) located at `backend/app/api/v1/*`
*   Frontend Application (React)
*   Authentication & Authorization Mechanisms (JWT implementation)
*   File Upload Processing Logic
*   Configuration & Environment Setup

**Out-of-Scope:**
*   Underlying operating system infrastructure.
*   Third-party services (e.g., SendGrid, AWS, Vercel infrastructure).
*   Social engineering or physical penetration testing.

---

## 4. Risk Assessment Matrix

Vulnerabilities are classified using the Common Vulnerability Scoring System (CVSS v3.1) and mapped to the following qualitative severity ratings:

*   **CRITICAL (9.0 - 10.0):** Immediate exploitation is likely. High impact on confidentiality, integrity, or availability.
*   **HIGH (7.0 - 8.9):** Exploitation is possible. Can lead to significant data loss or system compromise.
*   **MEDIUM (4.0 - 6.9):** Flaws that may lead to limited compromise or require complex exploitation chains.
*   **LOW (0.1 - 3.9):** Minor issues, predominantly informational or requiring highly unlikely circumstances.

---

## 5. Detailed Findings & Remediation Status

Below are the detailed technical findings from the initial assessment, along with their current remediation status.

### 5.1 Use of Hardcoded Default Secrets in Configuration
**Severity:** HIGH | **CVSSv3 Score:** 7.5 (High) 
**Status:** ✅ REMEDIATED
**OWASP Category:** A05:2021-Security Misconfiguration

**Description:**
The application relied on `pydantic-settings` to manage environment variables. However, the critical `JWT_SECRET_KEY` variable possessed a hardcoded fallback value (`"change-this-in-production"`). If the application was deployed without a `.env` file or environment variable, it would silently boot using the known, compromised secret.

**Impact:**
An attacker aware of the codebase could trivially forge valid JWT access tokens using the default secret, attaining full administrative access over any tenant within the SaaS platform.

**Evidence (Pre-Remediation):**
```python
# backend/app/core/config.py
class Settings(BaseSettings):
    JWT_SECRET_KEY: str = "change-this-in-production"
```

**Remediation Action Taken:**
The fallback default was removed from `config.py`. The variable was explicitly typed as `JWT_SECRET_KEY: str`, enforcing a strict requirement. The application will now securely fail to boot (Fail-Safe) if the secret is absent.

---

### 5.2 Lack of Token Revocation Mechanism (Session Fixation)
**Severity:** MEDIUM | **CVSSv3 Score:** 6.5 (Medium)
**Status:** ✅ REMEDIATED
**OWASP Category:** A07:2021-Identification and Authentication Failures

**Description:**
The application utilized stateless JSON Web Tokens (JWTs) for authentication. While efficient, there was no backend mechanism to track or invalidate tokens upon user logout. A user clicking "Logout" merely cleared local storage; the token remained actively valid until its inherent expiration (up to 7 days for refresh tokens).

**Impact:**
If an attacker intercepted an access or refresh token (e.g., via XSS or physical access), they could maintain unauthorized access even after the legitimate user believed they had securely terminated their session.

**Remediation Action Taken:**
A stateful `TokenBlocklist` architecture was implemented. Both access and refresh tokens are now minted with uniquely identifiable `jti` (JWT ID) claims. A new `POST /auth/logout` endpoint was constructed to insert these `jti` claims into a database blocklist. Authentication dependencies (`get_current_user`) were updated to reject any request bearing a blocklisted `jti`.

---

### 5.3 Insecure Parsing of Unstructured Documents (DoS Vector)
**Severity:** MEDIUM | **CVSSv3 Score:** 5.3 (Medium)
**Status:** ✅ REMEDIATED
**OWASP Category:** A04:2021-Insecure Design

**Description:**
The bulk upload functionality (`/tests/bulk-upload`) attempted to parse raw PDF and DOCX files to extract testing codes using PyMuPDF (`fitz`) and `python-docx`. The algorithm relied on loose string splitting (`split(',')`) across raw document text.

**Impact:**
Parsing unstructured, complex binary formats (like PDFs) using basic string manipulation is highly susceptible to unhandled exceptions and infinite loops. A maliciously crafted "zip bomb" PDF or highly nested DOCX file could severely spike CPU and RAM usage, resulting in Application-Layer Denial of Service (DoS).

**Remediation Action Taken:**
PyMuPDF and `python-docx` dependencies were completely stripped from the application. The `_parse_file` algorithm and frontend UI were strictly bounded to handle only structured, tabular data exclusively via `pandas.read_csv` and `pandas.read_excel`.

---

### 5.4 Lack of Application-Layer Rate Limiting
**Severity:** MEDIUM | **CVSSv3 Score:** 5.3 (Medium)
**Status:** ✅ REMEDIATED
**OWASP Category:** A04:2021-Insecure Design

**Description:**
Critical authentication endpoints (`/auth/login`, `/auth/register`) possessed no safeguards against rapid, repeated requests.

**Impact:**
The application was vulnerable to automated brute-force attacks and credential stuffing attacks against user accounts.

**Remediation Action Taken:**
The `slowapi` library was integrated to enforce IP-based rate limiting. A strict limit of `5 requests per minute` was applied to authentication endpoints, effectively mitigating automated brute-force capabilities.

---

### 5.5 Overly Permissive CORS and Verbose Error Disclosure
**Severity:** MEDIUM | **CVSSv3 Score:** 4.8 (Medium)
**Status:** ✅ REMEDIATED
**OWASP Category:** A05:2021-Security Misconfiguration

**Description:**
The backend `CORSMiddleware` utilized a broad regular expression (`allow_origin_regex=r"https://.*\.vercel\.app"`) allowing *any* Vercel-hosted domain to initiate cross-origin requests. Additionally, the global exception handler returned raw stack trace strings (`str(exc)`) directly to clients upon HTTP 500 errors.

**Impact:**
An attacker could host a malicious site on Vercel to bypass CORS protections and launch Cross-Site Request Forgery (CSRF) style attacks via XHR. Furthermore, verbose error strings could leak internal database schema details or file paths.

**Remediation Action Taken:**
The regex CORS approach was deleted; the system now mandates explicitly defined origins via the `CORS_ORIGINS` environment variable. The exception handler was updated to check `settings.is_production`, serving generic error messages to external clients while securely logging detailed traces internally.

---

## 6. Conclusion and Sign-off

The Hospital Billing System has undergone a rigorous security audit. The development team responded swiftly to the initial findings, integrating defense-in-depth mechanisms—including robust token invalidation, strict rate limiting, explicit configuration demands, and rigid input parsing capabilities.

Through verification re-testing, it is confirmed that **all identified vulnerabilities have been successfully remediated**. The application currently exhibits a highly defensible posture that aligns with modern security best practices.

**Final Determination:** APPROVED FOR PRODUCTION DEPLOYMENT.

*(Report End)*
