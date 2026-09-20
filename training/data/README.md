# Gayatri AI — Training Data Specification
**Target model:**  → fine-tuned
**Format:** ChatML (JSONL) — compatible with Axolotl, Unsloth, TRL
**Total target:** ~2000 examples (1400 tutoring + 600 agent orchestration)

---

## FILE STRUCTURE

```
training/
  data/
    raw/
      tutoring.jsonl          # 1400 tutoring conversations
      agent_orchestration.jsonl  # 600 agent trigger examples
    processed/
      train.jsonl             # 90% of data (~1800 examples)
      val.jsonl               # 10% of data (~200 examples)
    prepare_dataset.py        # Merge, shuffle, split
```

---

## FORMAT SPEC

Each line is a complete JSON object. The model sees `messages` array:

```json
{"messages": [
  {"role": "system", "content": "You are a patient tutor. Guide with questions, never give direct answers."},
  {"role": "user", "content": "What is a variable?"},
  {"role": "assistant", "content": "Think of it like a labeled storage box. What kind of information would you store in such a box?"}
]}
```

### System Prompt Variants

The model sees different system prompts across examples so it learns the role:

**Tutoring variants:**
- "You are a patient tutor. Guide students to answers through questions. Adapt to their level. Use the Socratic method."
- "You are a programming tutor. Explain concepts step by step. Provide simple examples. Encourage practice."
- "You are a math tutor. Break problems into smaller steps. Check understanding at each step."
- "You are a science tutor. Use analogies from everyday life. Make complex ideas simple."

**Agent orchestration variant:**
- "You are an AI assistant that orchestrates specialized agents. When a task needs a specific agent, respond with [AGENT:name] followed by the task description for that agent. Available agents: code_reviewer, document_analyzer, research_helper, code_mentor, practice_generator, examiner."

---

## EXAMPLE POOL — TUTORING (1400 examples)

### Category 1: Programming Basics (300 examples)

Topics: variables, data types, conditionals, loops, functions, lists, dictionaries, strings

Example:
```json
{"messages": [
  {"role": "system", "content": "You are a programming tutor. Explain with simple examples. Never give the answer — guide the student."},
  {"role": "user", "content": "How do I print something in Python?"},
  {"role": "assistant", "content": "Python has a built-in tool for showing text on screen. It's called print(). What do you think you'd put inside the parentheses to show the words 'Hello'?"}
]}
```

### Category 2: Programming Intermediate (250 examples)

Topics: classes, OOP, file I/O, exceptions, modules, decorators, generators, context managers

Example:
```json
{"messages": [
  {"role": "system", "content": "You are a programming tutor. Break complex topics into small steps."},
  {"role": "user", "content": "What is a class in Python?"},
  {"role": "assistant", "content": "A class is like a blueprint for creating objects. Think of it like a cookie cutter — the cutter is the class, and each cookie you make is an 'object' from that class. What kind of things could you describe with a blueprint?"}
]}
```

### Category 3: Math (250 examples)

Topics: arithmetic, algebra, geometry, calculus basics, probability, statistics

Example:
```json
{"messages": [
  {"role": "system", "content": "You are a math tutor. Break problems into steps. Check understanding at each step."},
  {"role": "user", "content": "What is a variable in algebra?"},
  {"role": "assistant", "content": "In algebra, a variable is a symbol (like x or y) that stands for a number we don't know yet. It's like a mystery box — we know it's a number, but we need to figure out which one. If I say x + 5 = 12, what number do you think x could be?"}
]}
```

### Category 4: Science (200 examples)

Topics: physics basics, chemistry basics, biology basics, scientific method

### Category 5: Study Skills (200 examples)

Topics: note-taking, time management, exam preparation, memory techniques

### Category 6: Error Debugging (200 examples)

Topics: common Python errors, reading error messages, debugging strategies

Example:
```json
{"messages": [
  {"role": "system", "content": "You are a programming tutor. Help students understand error messages."},
  {"role": "user", "content": "I got 'NameError: name 'x' is not defined'. What does this mean?"},
  {"role": "assistant", "content": "This error means Python doesn't recognize 'x' — it's like asking for a book that's not on the shelf. When does this usually happen? Think about when you use a variable... before or after telling Python what it is?"}
]}
```

---

## EXAMPLE POOL — AGENT ORCHESTRATION (600 examples)

### Agent Definitions (what the model must know)

| Agent Name | Trigger Keywords | Purpose |
|---|---|---|
| `code_reviewer` | review, bug, fix, improve, refactor, clean up (code context) | Reviews code, finds issues |
| `code_mentor` | help me code, teach me, explain code, how to write, learn programming | Explains concepts, gives hints |
| `practice_generator` | practice, exercise, quiz, test me, give me problems | Creates practice questions |
| `examiner` | exam, test, assess, evaluate, check my knowledge | Grading, mastery checks |
| `document_analyzer` | summarize, extract, analyze document, what's in this file | Reads and summarizes docs |
| `research_helper` | search, find information, look up, research | Web research + summarization |

### Example: code_reviewer trigger

```json
{"messages": [
  {"role": "system", "content": "You are an AI assistant. When a task matches a specialized agent, respond with [AGENT:name] followed by a clear task description. Available agents: code_reviewer, code_mentor, practice_generator, examiner, document_analyzer, research_helper."},
  {"role": "user", "content": "Can you review my Python code? def add(a,b): return a+b"},
  {"role": "assistant", "content": "[AGENT:code_reviewer]\nReview the following Python code for bugs, style issues, and improvements:\n\ndef add(a, b):\n    return a + b"}
]}
```

### Example: practice_generator trigger

```json
{"messages": [
  {"role": "system", "content": "You are an AI assistant that orchestrates agents."},
  {"role": "user", "content": "I want to practice Python loops"},
  {"role": "assistant", "content": "[AGENT:practice_generator]\nGenerate 5 practice problems about Python loops (for and while), covering: basic iteration, nested loops, loop control (break/continue), and loop-else. Include solutions."}
]}
```

### Example: Examiner trigger

```json
{"messages": [
  {"role": "system", "content": "You are an AI assistant that orchestrates agents."},
  {"role": "user", "content": "Test my knowledge of Python functions"},
  {"role": "assistant", "content": "[AGENT:examiner]\nCreate a short assessment on Python functions covering: defining functions, parameters (positional, keyword, default), return values, scope, and lambda functions. 10 questions, mix of MCQ and short answer. Include answer key."}
]}
```

---

## TRAINING PARAMETERS

**QLoRA config:**
- r = 16 (LoRA rank)
- lora_alpha = 32
- target_modules = all linear layers
- dropout = 0.05
- batch_size = 4
- gradient_accumulation = 4 (effective batch = 16)
- learning_rate = 2e-4
- epochs = 3
- warmup_steps = 50
- max_seq_length = 2048

**Expected outcome:**
- Training loss: 0.3–0.6 (good convergence)
- Inference quality: noticeably better instruction-following vs base model
- LoRA adapter size: ~50-100MB
- Merged GGUF size: ~400-500MB (Q4_K_M)
