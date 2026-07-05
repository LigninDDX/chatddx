ChatDDX

ChatDDX is an AI-assisted differential diagnosis support and model evaluation platform developed for emergency and acute care. The project explores how large language models can help generate, structure, and prioritize differential diagnoses from early clinical information, while also serving as a practical testbed for comparing frontier LLMs with locally hosted open-weight models.

ChatDDX is intended for research, evaluation, and prototyping rather than autonomous clinical use. Its purpose is to study whether AI can support diagnostic reasoning in acute care, improve the breadth and quality of differential diagnosis generation, and provide a framework for evaluating human–AI collaboration in emergency medicine.

⸻

Overview

Diagnostic reasoning in the emergency department often takes place under time pressure, incomplete information, and substantial uncertainty. ChatDDX was developed as a research platform to explore whether modern language models can assist clinicians by:

* generating relevant differential diagnoses from structured and free-text clinical input
* highlighting high-risk or time-critical “don’t miss” conditions
* helping structure diagnostic reasoning in a reproducible way
* enabling systematic evaluation of AI-assisted differential diagnosis in emergency medicine

In addition to its decision-support focus, ChatDDX functions as a model evaluation platform. The project is used to compare both frontier API-based LLMs and locally run open-weight models on clinically relevant diagnostic tasks, with attention to diagnostic quality, consistency, latency, privacy, and deployment feasibility.

⸻

Why ChatDDX

Generic chatbot interfaces can generate differential diagnoses, but they are not designed specifically for emergency medicine workflows or for structured evaluation across model families.

ChatDDX was built to provide a more focused framework for acute care diagnostic reasoning by combining:

* structured emergency-oriented clinical input
* differential diagnosis generation rather than generic conversational output
* prioritization of high-risk and “don’t miss” diagnoses
* a practical evaluation environment for comparing frontier and local models
* a foundation for future privacy-aware and institutionally controlled deployments

The goal is not simply to ask a language model for possible diagnoses, but to evaluate how different models perform when applied to clinically relevant differential diagnosis tasks in acute care.

⸻

Project Goals

The broader goals of ChatDDX include exploring whether AI support can:

* improve the quality and breadth of differential diagnoses
* reduce omission of important alternative diagnoses
* support more consistent diagnostic reasoning across clinicians
* identify potentially dangerous diagnoses earlier in the reasoning process
* serve as a platform for research on human–AI collaboration in acute care
* evaluate the feasibility of local, privacy-preserving inference for clinical decision support

⸻

Key Features

* AI-generated differential diagnoses based on structured and free-text clinical input
* Prioritized diagnostic suggestions rather than unstructured output
* Support for emergency-relevant reasoning, including potentially time-critical conditions
* Evaluation of multiple model classes, including frontier LLMs and local open-weight models
* Prototype interface for clinical case input
* Research-oriented architecture suitable for pilot studies, benchmarking, and model comparison
* Potential multilingual support, depending on model configuration

⸻

Intended Use

ChatDDX is intended for:

* research and development
* clinical education
* simulation and case-based learning
* evaluation of AI-assisted diagnostic support in emergency medicine
* benchmarking and comparison of LLMs for diagnostic reasoning tasks

It is not intended to function as an autonomous diagnostic system or as a replacement for physician assessment.

⸻

How It Works

At a high level, ChatDDX follows this workflow:

1. Clinical information is entered by the user, preferably by a clinician or other medically trained user, and may include:
    * age
    * symptoms
    * relevant medical history
    * vital signs
    * physical examination findings
    * selected laboratory or imaging findings
    * travel history or contextual risk factors when relevant
3. The case is structured and prepared for model inference.
4. A language model generates output, which may include:
    * a ranked differential diagnosis list
    * brief diagnostic reasoning
    * potentially dangerous diagnoses that should not be missed
5. The result is presented to the user as diagnostic decision support as a ranked list for further reflection and clinical assessment.

Depending on the implementation version, the system may include prompt templates, output formatting, and logic designed to improve consistency, usability, and clinical relevance.

⸻

Model Evaluation

A central part of ChatDDX is the evaluation of different model families for differential diagnosis support in acute care.

The project is used to compare:

* frontier LLMs, typically accessed through API-based inference
* locally hosted open-weight models, run on dedicated local hardware

The purpose is not only to assess diagnostic performance in absolute terms, but also to compare models across dimensions such as:

* differential diagnosis relevance and completeness
* prioritization of high-risk and “don’t miss” conditions
* consistency and reproducibility of outputs
* latency and usability in a clinical workflow
* feasibility of privacy-preserving local inference
* practical deployment constraints in healthcare environments

This allows ChatDDX to function not only as a diagnostic support interface, but also as a testbed for studying trade-offs between cloud-based frontier models and local models in real clinical use cases.

⸻

Deployment Modes

ChatDDX is designed to support multiple deployment and evaluation modes, including:

* frontier API-based models
* locally hosted open-weight models
* local inference workflows for privacy-sensitive or institutionally controlled environments

Part of the project involves testing local models on consumer GPU hardware, including:

* NVIDIA RTX 3090
* NVIDIA RTX 5090

This is intended to explore whether high-quality differential diagnosis support can be achieved outside of cloud-only deployments, and whether local inference can offer practical advantages in areas such as privacy, governance, cost control, and institutional flexibility.

⸻

Example Use Case

A clinician evaluates a patient in the emergency department with fever, abdominal pain, hypotension, and elevated inflammatory markers. ChatDDX can be used to generate a structured differential diagnosis list that may include, for example:

* sepsis of abdominal origin
* acute cholangitis
* perforated viscus
* mesenteric ischemia
* pyelonephritis
* pancreatitis

The output is meant to support the clinician’s reasoning process, not determine management independently.

⸻

Current Status

ChatDDX is currently a prototype / research-stage project with ethical approval.
The repository may contain experimental features, ongoing changes, and incomplete components as development continues.

This project should be considered an investigational tool rather than a finished product.

⸻

Safety and Important Limitations

ChatDDX is not a medical device and is not approved for autonomous clinical decision-making.

Important limitations include:

* outputs may be incomplete, incorrect, or misleading
* model performance depends heavily on input quality and prompt design
* the tool does not replace physician judgment, clinical examination, or standard diagnostic workup
* AI-generated suggestions must always be interpreted in clinical context
* the system may miss rare diagnoses or overemphasize plausible but incorrect alternatives
* performance may vary substantially across model versions and deployment configurations

Do not use ChatDDX as the sole basis for:

* diagnosis
* treatment decisions
* triage decisions
* disposition decisions
* emergency escalation decisions

⸻

Privacy and Data Handling

No personally identifiable patient data should be entered into the system unless the deployment environment is explicitly designed, approved, and secured for such use.

If used in research or development settings, users should ensure that:

* patient data is de-identified or pseudonymized when appropriate
* data handling complies with local legal, ethical, and institutional requirements
* external API use is evaluated from an information security and privacy perspective
* clinical data is managed according to applicable governance standards

⸻

Research Context

ChatDDX is part of a broader interest in AI-assisted diagnostic reasoning in emergency medicine and acute care. The project can be used as a platform for studying questions such as:

* How does AI affect the quality of physician-generated differential diagnoses?
* Does AI support reduce diagnostic omission?
* How do clinicians interact with AI-generated diagnostic suggestions?
* Can language models improve consistency in diagnostic reasoning across users?
* How do frontier LLMs compare with locally hosted models on clinically relevant diagnostic tasks?
* What are the practical trade-offs between API-based and local model deployment in healthcare?

⸻

Installation

Note: Update the commands below to match the actual project structure and framework used in this repository.

Clone the repository

git clone https://github.com/LigninDDX/chatddx.git
cd chatddx

Install dependencies

If using Node.js:

npm install

If using Python:

pip install -r requirements.txt

Configure environment variables

Create a local environment file and add the required API keys/settings, for example:

OPENAI_API_KEY=your_api_key_here

Run the application

Examples:

npm run dev

or

python app.py


⸻

Contributing

Contributions, feedback, and suggestions are welcome.

If you would like to contribute, please consider:

1. opening an issue to discuss bugs or feature ideas
2. submitting a pull request with a clear description of the change
3. documenting clinical, technical, or evaluation-related assumptions where relevant

⸻

Disclaimer

This repository is provided for research, development, and educational purposes only.

ChatDDX is not intended to replace clinical judgment, specialist consultation, local guidelines, or established diagnostic processes. No warranty is provided regarding diagnostic accuracy, safety, completeness, or fitness for clinical use.

Use of this repository and any associated outputs is entirely at the user’s own risk.

⸻

Contact

For questions, collaboration, or research-related inquiries, please open an issue in this repository or contact the project maintainers.

