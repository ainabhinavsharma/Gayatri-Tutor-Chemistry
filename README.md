# Gayatri Tutor V3 🎓

> **A Next-Generation, Local-First Agentic AI Platform**  
> *Developed with pride under the [DBERT Internship Program](https://dbert.online)*

Gayatri Tutor V3 is an advanced, local-first desktop application designed to revolutionize personalized learning and AI assistance. By combining a locally-hosted fine-tuned Large Language Model (LLM) with a sophisticated agentic architecture, it provides an intelligent and privacy-controlled learning environment.

This project was built from the ground up to demonstrate how specialized AI agents, orchestrated by a central locally-running brain, can securely tutor students, execute complex tools, and seamlessly bridge local inference with cloud APIs when needed.

---

## 🌟 What This Project Does

- **Intelligent Orchestration:** A central local LLM routes user requests to specialized AI agents (e.g., Code Reviewer, Math Tutor, General Assistant) based on context and need.
- **Privacy Controlled by Design:** The app supports precise data boundary control:
  - **Local-Only Mode (Default):** All primary inference happens entirely on your local machine using quantized GGUF models. Conversation content stays on-device except for explicitly invoked local dependencies.
  - **Cloud-Allowed Mode:** User-approved provider calls may transmit submitted content according to the provider's policy.
- **Interactive Tutoring Engine:** Tracks student mastery over concepts using a Learning Dependency Graph and adapts responses dynamically to foster actual learning rather than just providing answers.
- **Beautiful & Native Desktop UI:** Built using PySide6 and a modern WebEngine front-end, bridging smooth web technologies with robust Python backend logic.

---

## 🚀 Getting Started

Follow these steps to set up the project on your local Windows machine.

### Prerequisites
- **Python:** 3.12.x (`>=3.12, <3.13` required for binary wheel and C++ extension compatibility)
- **Git:** Installed and available on system PATH

### 1. Setup the Environment
Clone the repository and run the setup script to configure your virtual environment and install dependencies:
```bash
git clone https://github.com/Gayatri-Education/Gayatri-Tutor-V3.git
cd Gayatri-Tutor-V3
setup.bat
```

### 2. Launch the Application
Once the dependencies are installed and the model is acquired, you can run the application normally:
```bash
launch.bat
```

**Debug Mode:**
If you want to view real-time application logs (useful for checking agent dispatches, model loading, and database queries), use the debug script instead:
```bash
run_gayatri.bat
```
*(Alternatively, you can manually activate the environment and run `python -m app.main` with the `GAYATRI_LOG_LEVEL=DEBUG` environment variable set)*

---

## 🧠 Model Training & Integration

The intelligence of Gayatri Tutor is powered by a custom fine-tuned model. The repository includes the complete pipeline used to generate data and fine-tune the model.

1. **Generate Data:** Run `python training/generate_data.py` to produce a diverse set of training examples.
2. **Fine-Tune:** Upload `training/colab_notebook.py` to Google Colab to execute the QLoRA fine-tuning process.
3. **Deploy:** Download the resulting `.gguf` file and place it in the models directory: `%LOCALAPPDATA%\GayatriAI\models\gayatri\`.

---

## 🏗️ Technology Stack

| Component | Technology |
|---|---|
| **UI Framework** | PySide6 + QWebEngine + QWebChannel |
| **Local Inference** | GGUF → llama-cpp-python |
| **Model Training** | QLoRA via Unsloth (Google Colab) |
| **Database & Persistence**| SQLite + sqlite-vec |
| **Security & Secrets** | Windows DPAPI |
| **Testing & Quality** | `pytest`, `pytest-qt`, `ruff` |

---

## 📜 License

**Educational / Personal Use Only — Commercial Use Prohibited**

This repository is publicly available for educational, academic, research, and personal learning purposes. You are welcome to read, study, and modify the source code for your own non-commercial educational or personal use.

Commercial use, redistribution, resale, incorporation into commercial products or services, SaaS deployment, and development of competing commercial products are strictly prohibited without prior written permission from Gayatri Education.

Please see the [LICENSE.md](LICENSE.md) file for the complete terms.

*Copyright © 2026 Gayatri Education. All Rights Reserved.*


## 🤝 Contributing & Help Wanted

We are actively looking for open-source contributors on GitHub to help us fix issues and improve the project!

To get started, read our [CONTRIBUTING.md](CONTRIBUTING.md) guide. We welcome all Pull Requests!
