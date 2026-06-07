import json, urllib.request, urllib.error, time

with open("config/api_keys.json") as f:
    k = json.load(f)

tests = []

# Cerebras
for i, key in enumerate([k.get("cerebras_api_key",""), k.get("cerebras_api_key2","")], 1):
    if not key: continue
    body = json.dumps({"model":"gpt-oss-120b","messages":[{"role":"user","content":"hi"}],"max_tokens":5}).encode()
    req = urllib.request.Request("https://api.cerebras.ai/v1/chat/completions", data=body,
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        tests.append(f"  Cerebras {i}: OK (HTTP {r.status})")
    except urllib.error.HTTPError as e:
        tests.append(f"  Cerebras {i}: FAIL (HTTP {e.code}) - {e.read().decode()[:100]}")
    except Exception as e:
        tests.append(f"  Cerebras {i}: ERROR - {e}")
    time.sleep(1)

# Groq
for i, key in enumerate([k.get("groq_api_key",""), k.get("groq_api_key2","")], 1):
    if not key: continue
    body = json.dumps({"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"hi"}],"max_tokens":5}).encode()
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body,
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        tests.append(f"  Groq {i}: OK (HTTP {r.status})")
    except urllib.error.HTTPError as e:
        tests.append(f"  Groq {i}: FAIL (HTTP {e.code}) - {e.read().decode()[:100]}")
    except Exception as e:
        tests.append(f"  Groq {i}: ERROR - {e}")
    time.sleep(1)

# Gemini
gemini_keys = [k.get("gemini_api_key",""), k.get("gemini_api_key_fallback",""), k.get("gemini_api_key3",""), k.get("gemini_api_key4","")]
for i, key in enumerate(gemini_keys, 1):
    if not key: continue
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + key
    body = json.dumps({"contents":[{"parts":[{"text":"hi"}]}]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        tests.append(f"  Gemini {i}: OK (HTTP {r.status})")
    except urllib.error.HTTPError as e:
        tests.append(f"  Gemini {i}: FAIL (HTTP {e.code}) - {e.read().decode()[:100]}")
    except Exception as e:
        tests.append(f"  Gemini {i}: ERROR - {e}")
    time.sleep(1)

print("API KEY STATUS:")
for t in tests:
    print(t)
