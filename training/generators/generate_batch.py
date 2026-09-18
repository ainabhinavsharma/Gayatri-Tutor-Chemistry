import json
import os
import random
import argparse

SYSTEM_PROMPT = """You are Gayatri Chemistry Tutor.
You teach Chemistry in an NCERT/CBSE-oriented educational setting.
Your current supported domains are:
1. Thermodynamics
2. Inorganic Chemistry
You are an adaptive teacher.
When appropriate:
Explain -> example -> ask -> evaluate -> adapt -> continue."""

THERMO_TOPICS = ["First Law", "Hess's Law", "Gibbs Free Energy", "Heat Capacity", "Enthalpy of Formation"]
INORG_TOPICS = ["s-block Reactivity", "p-block Trends", "d-block Oxidation States", "Hydrogen Preparation", "Coordination Compounds"]
LEVELS = ["Class 11", "Class 12"]
INTERACTIONS = ["explain_example_ask", "socratic_questioning", "hint_generation", "student_evaluation"]

def generate_batch(output_path, num_thermo, num_inorganic):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    examples = []
    
    # Generate Thermo
    for i in range(num_thermo):
        t_topic = random.choice(THERMO_TOPICS)
        q_val = random.randint(10, 500)
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Can you explain {t_topic} with an example involving {q_val} Joules?"},
                {"role": "assistant", "content": f"Sure! Let's talk about {t_topic}. If a system absorbs {q_val} J of heat...\n\nWhat would happen if the work done by the system is {q_val // 2} J?"},
                {"role": "user", "content": f"The change in internal energy would be {q_val - (q_val // 2)} J."},
                {"role": "assistant", "content": "Correct! You successfully applied the First Law of Thermodynamics."}
            ],
            "metadata": {
                "domain": "thermodynamics",
                "topic_id": t_topic.lower().replace(" ", "_"),
                "subtopic_id": "concept_application",
                "difficulty": random.randint(1, 4),
                "interaction_type": random.choice(INTERACTIONS),
                "question_type": "numerical",
                "class_level": "Class 11",
                "source_id": "NCERT_CH6",
                "source_reference": "Class 11 Chemistry Part 1, Chapter 6",
                "verified": True,
                "retrieval_context_used": False,
                "source_grounding": "NCERT",
                "numerical_metadata": {
                    "given": [f"q = {q_val} J", f"w = {-q_val//2} J"],
                    "required": "delta U",
                    "formula": "delta U = q + w",
                    "substitution": f"delta U = {q_val} - {q_val//2}",
                    "expected_answer": str(q_val - (q_val // 2)),
                    "unit": "J",
                    "tolerance": "0"
                }
            }
        })
        
    # Generate Inorganic
    for i in range(num_inorganic):
        i_topic = random.choice(INORG_TOPICS)
        elem = random.choice(["Na", "K", "Mg", "Ca", "B", "Al", "C", "Si"])
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"I'm confused about {i_topic}, especially regarding {elem}."},
                {"role": "assistant", "content": f"Let's look at {elem} in the context of {i_topic}. {elem} is known for specific periodic trends. For example, its ionization enthalpy behaves differently than its neighbors.\n\nCan you tell me how you think the atomic radius of {elem} compares to the element directly below it?"},
                {"role": "user", "content": f"The atomic radius of {elem} is smaller than the one below it because of added shells."},
                {"role": "assistant", "content": "Exactly! The principal quantum number increases as you go down the group, adding new electron shells."}
            ],
            "metadata": {
                "domain": "inorganic_chemistry",
                "topic_id": i_topic.lower().replace(" ", "_"),
                "subtopic_id": "periodic_trends",
                "difficulty": random.randint(1, 3),
                "interaction_type": random.choice(INTERACTIONS),
                "question_type": "conceptual",
                "class_level": random.choice(LEVELS),
                "source_id": "NCERT_INORG",
                "source_reference": "NCERT Inorganic Chapters",
                "verified": True,
                "retrieval_context_used": False,
                "source_grounding": "NCERT"
            }
        })
        
    # Introduce some exact duplicates intentionally to test deduplication
    for _ in range(50):
        examples.append(examples[0])
        
    random.shuffle(examples)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
            
    print(f"Generated {len(examples)} batch examples at {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="../../datasets/chemistry/raw/batch_001.jsonl")
    parser.add_argument("--thermo", type=int, default=1000)
    parser.add_argument("--inorganic", type=int, default=1000)
    args = parser.parse_args()
    
    generate_batch(os.path.abspath(args.output), args.thermo, args.inorganic)
