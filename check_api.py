import requests, PyPDF2, os, json

folder = r'C:\Users\tssat\Downloads\archive (1)\data\data\INFORMATION-TECHNOLOGY'
f = open(os.path.join(folder, os.listdir(folder)[0]), 'rb')
text = ' '.join(p.extract_text() for p in PyPDF2.PdfReader(f).pages)

r = requests.post('http://localhost:8000/nlp/screen', json={
    'jd_text': 'Python SQL AWS Docker Linux',
    'resume_texts': [text],
    'top_n': 1
})

print(json.dumps(r.json(), indent=2))