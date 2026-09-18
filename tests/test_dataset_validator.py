
from training.validators.dataset_validator import DatasetValidator

def test_clean_dataset_passes():
    validator = DatasetValidator()
    data = [
        {'messages': [{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': 'hello'}]}
    ]
    assert len(validator.validate_dataset(data)) == 0

def test_empty_message_check():
    validator = DatasetValidator()
    data = [
        {'messages': [{'role': 'user', 'content': ' '}]}
    ]
    errors = validator.validate_dataset(data)
    assert len(errors) == 1
    assert 'empty message' in errors[0]

def test_role_check():
    validator = DatasetValidator()
    data = [
        {'messages': [{'role': 'human', 'content': 'hi'}]}
    ]
    errors = validator.validate_dataset(data)
    assert len(errors) == 1
    assert 'invalid role' in errors[0]

def test_duplicate_check():
    validator = DatasetValidator()
    data = [
        {'messages': [{'role': 'user', 'content': 'hi'}]},
        {'messages': [{'role': 'user', 'content': 'hi'}]}
    ]
    errors = validator.validate_dataset(data)
    assert len(errors) == 1
    assert 'duplicate' in errors[0]

def test_conflict_check():
    validator = DatasetValidator()
    data = [
        {'messages': [{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': 'hello'}]},
        {'messages': [{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': 'hey'}]}
    ]
    errors = validator.validate_dataset(data)
    assert len(errors) == 1
    assert 'conflicting' in errors[0]

def test_length_check():
    validator = DatasetValidator()
    data = [
        {'messages': [{'role': 'user', 'content': 'a' * 33000}]}
    ]
    errors = validator.validate_dataset(data)
    assert len(errors) == 1
    assert 'exceeds length' in errors[0]

def test_pii_check():
    validator = DatasetValidator()
    data = [
        {'messages': [{'role': 'user', 'content': 'my email is a@b.com'}]}
    ]
    errors = validator.validate_dataset(data)
    assert len(errors) == 1
    assert 'PII (email)' in errors[0]
    
    data2 = [
        {'messages': [{'role': 'user', 'content': 'call me at 123-456-7890'}]}
    ]
    errors2 = validator.validate_dataset(data2)
    assert len(errors2) == 1
    assert 'PII (phone)' in errors2[0]

def test_code_fence_check():
    validator = DatasetValidator()
    data = [
        {'messages': [{'role': 'user', 'content': 'here is code: ```python print(1)'}]}
    ]
    
    errors = validator.validate_dataset(data)
    assert len(errors) == 1
    assert 'unclosed code' in errors[0]
