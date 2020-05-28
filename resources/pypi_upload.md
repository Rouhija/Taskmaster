### Publishing

Test locally
```sh
virtualenv venv -p python3 && source venv/bin/activate
pip install -r requirements.txt
```

Compile and upload
```sh
# Test
python3 setup.py develop
# Compile
python setup.py bdist_wheel
# Upload
python -m twine upload dist/*
# Upgrade
pip install taskmaster --upgrade
```

### Dependencies
- tqdm==4.45.0
- twine==3.1.1