from django.http import HttpResponse


def api_playground(request):
    html = '''<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>API Playground</title>
    <style>body{font-family:system-ui,Arial;margin:20px} textarea{width:100%;height:120px}</style>
  </head>
  <body>
    <h2>Cakto Mini Split Engine — Playground</h2>
    <p>Use the form below to test endpoints. The playground avoids external CDN.</p>

    <h3>Endpoint: POST /api/v1/checkout/quote</h3>
    <textarea id="quote_body">{"amount":"297.00","currency":"BRL","payment_method":"card","installments":3,"splits":[{"recipient_id":"producer_1","role":"producer","percent":70},{"recipient_id":"affiliate_9","role":"affiliate","percent":30}]}</textarea>
    <button onclick="call('/api/v1/checkout/quote', false)">Send Quote</button>

    <h3>Endpoint: POST /api/v1/payments</h3>
    <textarea id="payments_body">{"amount":"297.00","currency":"BRL","payment_method":"card","installments":3,"splits":[{"recipient_id":"producer_1","role":"producer","percent":70},{"recipient_id":"affiliate_9","role":"affiliate","percent":30}]}</textarea>
    <p>Idempotency-Key: <input id="idempotency" /></p>
    <button onclick="call('/api/v1/payments', true)">Send Payment</button>

    <h3>Response</h3>
    <pre id="out"></pre>

    <script>
    async function call(path, includeIdempotency){
      const out = document.getElementById('out');
      out.textContent = '...loading';
      let body = document.getElementById(includeIdempotency? 'payments_body':'quote_body').value;
      try{ body = JSON.parse(body); }catch(e){ out.textContent = 'Invalid JSON body'; return }
      const headers = {'Content-Type':'application/json'};
      if(includeIdempotency){ const k = document.getElementById('idempotency').value; if(k) headers['Idempotency-Key']=k }
      try{
        const resp = await fetch(path, {method:'POST', headers, body: JSON.stringify(body)});
        const text = await resp.text();
        out.textContent = 'Status: '+resp.status+'\n'+text;
      }catch(e){ out.textContent = 'Fetch error: '+e }
    }
    </script>
  </body>
</html>
'''
    return HttpResponse(html)
