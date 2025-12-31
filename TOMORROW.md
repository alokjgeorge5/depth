# Testing Plan - Dec 31, 2025

## ⏰ Wake up: 5:30 AM (tokens reset)

### Test Sequence (30 min total):

#### 1. Health Check (1 min)
```javascript
// In browser console at http://localhost:5000/
fetch('/health').then(r => r.json()).then(console.log);
```
**Expected:** `{"status": "ok", "groq_api": "✓", "personas_loaded": 4}`

---

#### 2. Single Request Test (5 min)
```javascript
fetch('/api/getResponses', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: 'Should I launch my product?'})
}).then(r => r.json()).then(d => {
    console.log('Responses:', d.responses.length);
    console.log('Time:', d.responses[0]?.content?.length, 'chars');
});
```
**Expected:** 4 responses, each 100-500 chars

---

#### 3. Sequential Stress Test (10 min)
```javascript
async function sequentialTest() {
    const questions = [
        'What are the risks?',
        'How do I validate the idea?',
        'What is the MVP?',
        'When should I launch?',
        'How do I get users?'
    ];
    
    for (let i = 0; i < questions.length; i++) {
        console.log(`\n[${i+1}/5] ${questions[i]}`);
        const start = Date.now();
        
        const res = await fetch('/api/getResponses', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question: questions[i]})
        });
        
        const data = await res.json();
        const duration = Date.now() - start;
        
        console.log(`✅ ${data.responses?.length || 0} responses in ${duration}ms`);
        
        await new Promise(r => setTimeout(r, 2000)); // 2s gap
    }
    console.log('\n✅ SEQUENTIAL TEST COMPLETE');
}

sequentialTest();
```
**Expected:** 5/5 succeed, each <10s

---

#### 4. Concurrent Test (5 min)
```javascript
async function concurrentTest() {
    console.log('🔥 CONCURRENT TEST: 2 requests...\n');
    
    const promises = [
        fetch('/api/getResponses', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question: 'Test A'})
        }),
        fetch('/api/getResponses', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question: 'Test B'})
        })
    ];
    
    const start = Date.now();
    const results = await Promise.allSettled(promises);
    const duration = Date.now() - start;
    
    const succeeded = results.filter(r => r.status === 'fulfilled').length;
    console.log(`✅ ${succeeded}/2 succeeded in ${duration}ms`);
}

concurrentTest();
```
**Expected:** 2/2 succeed

---

#### 5. If All Pass → Deploy to Railway (30 min)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up

# Get URL
railway domain
```

---

## 📊 Token Budget for Tomorrow:
- **Available:** 100,000 tokens (fresh reset at 5:30 AM)
- **Per question:** ~6,000 tokens (4 personas × 1500 tokens each)
- **Max questions:** ~16 questions
- **Testing budget:** 8 questions (50%)
- **Deployment testing:** 8 questions (50%)

---

## 🎯 Success Criteria:
- [ ] Health check passes
- [ ] Single request works
- [ ] 5/5 sequential requests succeed
- [ ] 2/2 concurrent requests succeed
- [ ] Deploy to Railway
- [ ] Test live URL
- [ ] **LAUNCH** 🚀

---

## ⚠️ If Tests Fail:
1. Check backend logs for errors
2. Verify Groq API key is valid
3. Check token usage at https://console.groq.com
4. If rate limited again → upgrade to paid ($5/month)

---

## 📅 Timeline:
- **5:30 AM** - Start testing
- **6:00 AM** - Deploy to Railway
- **6:30 AM** - Live on internet
- **7:00 AM** - Share on Twitter/Reddit
- **8:00 AM** - First real users! 🎉
