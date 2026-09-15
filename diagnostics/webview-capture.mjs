// Read-only inspection of the explicitly enabled localhost WebView2 debugger.
// Never log navigation URLs, DOM text, cookies, storage, or authentication data.
import {mkdir, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
const output = process.argv[2];
const deadline = setTimeout(()=>{console.error('Browser capture exceeded 50 seconds');process.exit(124);},50000);
await mkdir(output, {recursive:true, mode:0o700});
let response;
for (let attempt=0; attempt<30; attempt++) {
  try { response=await fetch('http://127.0.0.1:19223/json/list', {signal:AbortSignal.timeout(1000)}); break; }
  catch (error) { if(attempt===29)throw error; await new Promise(resolve=>setTimeout(resolve,1000)); }
}
if (!response.ok) throw new Error(`Diagnostic HTTP ${response.status}`);
const pages = (await response.json()).filter(t => t.type === 'page');
for (const [i, page] of pages.entries()) {
  const target = new URL(page.webSocketDebuggerUrl);
  if (target.hostname !== '127.0.0.1' || target.port !== '19223') throw new Error('Unexpected diagnostic host');
  const ws = new WebSocket(target);
  await new Promise((resolve,reject) => {
    const timer=setTimeout(()=>{ws.close();reject(new Error('CDP connection timeout'));},5000);
    ws.onopen=()=>{clearTimeout(timer);resolve();};
    ws.onerror=error=>{clearTimeout(timer);reject(error);};
  });
  let id=0;
  async function rpc(method,params={}) {
    const request=++id;
    return await new Promise((resolve,reject) => {
      const timer=setTimeout(()=>{ws.removeEventListener('message',listener);reject(new Error(`CDP timeout: ${method}`));},10000);
      function listener(e) {const r=JSON.parse(e.data);if(r.id!==request)return;clearTimeout(timer);ws.removeEventListener('message',listener);if(r.error)reject(new Error(r.error.message));else resolve(r.result);}
      ws.addEventListener('message',listener);
      ws.send(JSON.stringify({id:request,method,params}));
    });
  }
  try {
    const dom=await rpc('Runtime.evaluate',{expression:'JSON.stringify({ready:document.readyState,elements:document.querySelectorAll("*").length,bodyCharacters:document.body?.innerText.length,images:document.images.length})',returnByValue:true});
    console.log(JSON.stringify({page:i,origin:new URL(page.url).origin,dom:JSON.parse(dom.result.value)}));
    const shot=await rpc('Page.captureScreenshot',{format:'png'});
    const path=join(output,`webview-page-${i}.png`);
    await writeFile(path,Buffer.from(shot.data,'base64'),{mode:0o600});
    console.log(JSON.stringify({page:i,origin:new URL(page.url).origin,dom:JSON.parse(dom.result.value),screenshot:path}));
  } finally {ws.close();}
}
clearTimeout(deadline);
