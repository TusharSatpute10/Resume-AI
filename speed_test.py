import time, requests, os, PyPDF2

folder = r'C:\Users\tssat\Downloads\archive (1)\data\data\INFORMATION-TECHNOLOGY'
pdfs = [f for f in os.listdir(folder) if f.endswith('.pdf')][:10]

resume_texts = []
for pdf in pdfs:
    with open(os.path.join(folder, pdf), 'rb') as f:
        text = ' '.join(p.extract_text() for p in PyPDF2.PdfReader(f).pages)
        resume_texts.append(text)
        print(f"Loaded: {pdf} ({len(text)} chars)")

jd_text = 'Senior IT Manager with 5+ years experience. Required skills: Python, SQL, AWS, Docker, Linux, Active Directory, Windows Server, networking, project management.'

print("\nRunning NLP screening on 10 resumes...")
t = time.perf_counter()
r = requests.post('http://localhost:8000/nlp/screen', json={
    'jd_text': jd_text,
    'resume_texts': resume_texts,
    'top_n': 10
})
total = round(time.perf_counter() - t, 2)
print(f"\nTotal time for 10 resumes: {total}s")

if r.status_code != 200:
    print("Error:", r.status_code, r.text[:300])
else:
    data = r.json()
    print("\nTop 5 Results:")
    print("-" * 60)
    for c in data.get('candidates', [])[:5]:
        name = c.get('name', 'Unknown')
        score = c.get('nlp_score', 0)
        rec = c.get('recommendation', '?')
        skills = len(c.get('matched_skills', []))
        print(f"  {name} | Score: {score:.1f} | {rec} | Matched skills: {skills}")