# Gayatri Tutor V3 Privacy Contract

## 1. Principles
- **User Control:** The user is the ultimate owner of their data.
- **Data Minimization:** No data leaves the device unless explicitly required and authorized.
- **Transparency:** All external communications are logged and auditable.

## 2. Execution Modes

### Local-Only Mode (Default)
- **Primary Inference:** All LLM inference happens entirely on the local machine using quantized models.
- **Data Boundary:** Conversation content, including student answers and mastery evaluations, **never leaves the device**.

### Cloud-Allowed Mode (Opt-in)
- **Primary Inference:** The user may select cloud providers (e.g., OpenAI, Anthropic, Google) for faster or more capable inference.
- **Data Boundary:** Prompts (including conversation history and context) are transmitted to the selected cloud provider.
- **Auditing:** Every request sent to a cloud provider in this mode is logged with a TRANSMISSION_AUDIT entry, capturing the provider name, key reference, and timestamp.

## 3. Tool Execution
- **Tool Arguments:** Arguments passed to tools are validated against strict schemas to prevent command injection and path traversal.
- **Tool Logging:** All tool invocations are centrally logged with arguments and execution status for auditing.

## 4. Consent and Disclosure
- The privacy mode is explicitly toggled by the user in the Settings UI.
- The application will strictly refuse to send data to any cloud provider if privacy_mode is set to local_only, enforcing the boundary at the network request level.
