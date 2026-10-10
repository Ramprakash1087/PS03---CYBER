import json
from pathlib import Path

from backend.ai_analyzer import analyze_audit


def main() -> None:
    data_path = Path(__file__).with_name('hackathon_dataset.json')
    examples = json.loads(data_path.read_text(encoding='utf-8'))
    correct = 0
    total = 0
    for example in examples:
        claims = list(example['expected'].keys())
        result = analyze_audit(claims, example['landing_page_text'])
        verdicts = {c['claim']: c['verdict'] for c in result['claims']}
        for claim, expected in example['expected'].items():
            total += 1
            if verdicts.get(claim) == expected:
                correct += 1
    accuracy = (correct / total) * 100 if total else 0
    print(f'Correct matches: {correct}/{total} ({accuracy:.1f}%)')


if __name__ == '__main__':
    main()
