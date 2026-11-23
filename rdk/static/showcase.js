/* BlackDeck LabOS visual cockpit: no remote JS/CSS dependencies.
 * Database replay is distinct from hardware live mode and synthetic display.
 * Ring positions are decorative, NEVER physical bearings or triangulation.
 */
(() => {
 'use strict';
 const byId = id => document.getElementById(id);
 const stage=byId('showcaseStage');
 if(!stage)return;
 const canvas=byId('showcaseCanvas');
 const ctx=canvas.getContext('2d', {alpha:false});
 if(!ctx)return;
 let mode='replay', active=true, rows=[],frame=0,w=800,h=400,lastFrame=0;
 let lastFetch=0, refreshInFlight=false;
 const set=(id,s)=>{const el=byId(id);if(el)el.textContent=String(s)};
 const colorByKind={rf:'#edc47b',wifi:'#ad92ef',ble:'#d590e4',nfc:'#f5dca7',system:'#baa9cb'};
 function adjust(){
   const bounds=canvas.getBoundingClientRect();
   if(!bounds.width || !bounds.height)return;
   const dpr=Math.min(window.devicePixelRatio||1,2);
   w=bounds.width;h=bounds.height;
   canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
   ctx.setTransform(dpr,0,0,dpr,0,0);
 }
 window.addEventListener('resize',adjust);
 function fakeRows(){
   const list=[];
   for(let i=0;i<30;i++){
     const kind=['rf','wifi','ble','rf','nfc','rf'][i%6];
     const rssi=kind==='nfc'?null:-48-35*Math.abs(Math.sin(i*0.93));
     list.push({id:i+1,kind,source:'simulated',stamp_utc:'',
       data: kind==='rf'?{rssi,frequency_hz:433920000,sample_index:i}:
             kind==='wifi'?{rssi,channel:1+i%11}:
             kind==='ble'?{rssi}: {tag_type:'NFC-A demo'}});
   }
   return list;
 }
 function updateFacts(){
   const rf=rows.filter(x=>x.kind==='rf' && Number.isFinite(x.data?.rssi));
   const kinds=new Set(rows.map(x=>x.kind));
   const sources=new Set(rows.map(x=>x.source));
   set('showCount',rows.length);
   set('showRssi',rf.length?(rf.reduce((t,x)=>t+x.data.rssi,0)/rf.length).toFixed(1):'—');
   set('showKinds',kinds.size);
   set('showSource',mode==='demo'?'SIMULATED · NOT SAVED':(sources.size?[...sources].join(' / '):'NO RECORDS'));
   set('showModeText',mode==='demo'?'VISUAL DEMO / SYNTHETIC':'DATABASE REPLAY / STORED');
   set('showWatermark',mode==='demo'?'SIMULATED · NO RF HARDWARE':'SAVED DATA · NOT LIVE SENSOR');
   set('showState',active?'ANIMATED':'PAUSED');
   byId('showEvidence').classList.toggle('active',mode==='replay');
   byId('showDemo').classList.toggle('active',mode==='demo');
   byId('showPause').textContent=active?'暂停动画':'继续动画';
   const root=byId('showEvents');root.replaceChildren();
   if(!rows.length){const p=document.createElement('p');p.textContent='没有历史记录；可切换视觉模拟模式演示动效。';root.append(p);return;}
   for(const item of rows.slice(-8).reverse()){
     const node=document.createElement('div'); node.className='event';
     const a=document.createElement('strong');a.textContent=item.kind.toUpperCase()+' / '+item.source;
     const b=document.createElement('span');
     const d=item.data||{};
     const details=item.kind==='rf'?`${d.frequency_hz||'?'} Hz · ${d.rssi??'—'} dBm`:
       item.kind==='wifi'?`ch ${d.channel??'?'} · ${d.rssi??'—'} dBm`:
       item.kind==='ble'?`RSSI ${d.rssi??'—'} dBm`:
       item.kind==='nfc'?(d.tag_type||'NFC tag'):'system';
     b.textContent=details;node.append(a,b);root.append(node);
   }
 }
 async function loadRecords(force=false){
   if(mode!=='replay'||refreshInFlight)return;
   if(!force && Date.now()-lastFetch<9000)return;
   refreshInFlight=true;
   try {
     const res=await fetch('/api/samples',{cache:'no-store'});
     if(!res.ok)throw new Error(`HTTP ${res.status}`);
     const data=await res.json();
     if(!Array.isArray(data))throw new Error('records not an array');
     // Limit visual workload. The database remains unchanged.
     rows=data.filter(x=>x && typeof x==='object' && x.data && typeof x.data==='object').slice(-400);
     lastFetch=Date.now();updateFacts();
   } catch(e){set('showState','连接失败');set('showSource',String(e.message).slice(0,48))}
   finally{refreshInFlight=false}
 }
 const line=(x1,y1,x2,y2,col,width=1)=>{ctx.strokeStyle=col;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke()};
 function draw(now){
   requestAnimationFrame(draw);
   if(!stage.closest('.page')?.classList.contains('active') || !active)return;
   if(now-lastFrame<33)return;
   lastFrame=now;frame++;
   if(Date.now()-lastFetch>9000 && mode==='replay')loadRecords();
   const g=ctx.createLinearGradient(0,0,w,h);g.addColorStop(0,'#120a20');g.addColorStop(0.58,'#27183d');g.addColorStop(1,'#0d0818');
   ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
   // Graticule for visual design, not calibrated axes.
   for(let x=15;x<w;x+=38)line(x,10,x,h-12,'#8b61ab24');
   for(let y=15;y<h;y+=38)line(10,y,w-10,y,'#8b61ab24');
   const cx=w*.365,cy=h*.46,r=Math.min(w*.255,h*.395);
   ctx.save();ctx.translate(cx,cy);
   for(const pct of [.25,.5,.75,1]){
     ctx.beginPath();ctx.arc(0,0,r*pct,0,Math.PI*2);ctx.strokeStyle=pct===1?'#edc47b99':'#ad83d15e';ctx.lineWidth=pct===1?1.6:1;ctx.stroke();
   }
   line(-r-20,0,r+20,0,'#9374ae64');line(0,-r-20,0,r+20,'#9374ae64');
   ctx.fillStyle='#f2cc87';ctx.fillRect(-2,-2,4,4);
   let angle=frame*.018;
   ctx.beginPath();ctx.moveTo(0,0);ctx.arc(0,0,r,angle-.52,angle);ctx.closePath();
   const rg=ctx.createRadialGradient(0,0,0,0,0,r);rg.addColorStop(0,'#dab0ec39');rg.addColorStop(1,'#b879e804');ctx.fillStyle=rg;ctx.fill();
   line(0,0,Math.cos(angle)*r,Math.sin(angle)*r,'#f1c578',2);
   // Decorative distribution of stored samples; angle != bearing.
   const show=rows.slice(-70);
   for(let i=0;i<show.length;i++){
     const item=show[i];const signal=item.data?.rssi;
     const strength=Number.isFinite(signal)?Math.max(0,Math.min(1,(signal+120)/95)):.25;
     const phi=i*2.39996+.7;
     const dist=r*(.16+.78*(1-strength));
     const px=Math.cos(phi)*dist,py=Math.sin(phi)*dist;
     const clr=colorByKind[item.kind]||'#ceafe6';
     ctx.globalAlpha=.45+.4*Math.sin(frame*.037+i);
     ctx.beginPath();ctx.arc(px,py,item.kind==='nfc'?3.6:2.7,0,Math.PI*2);ctx.fillStyle=clr;ctx.fill();
   }
   ctx.restore();ctx.globalAlpha=1;
   // RSSI history plot: the horizontal index reflects sample order, not time-calibrated frequency.
   const plot={x:w*.67,y:h*.16,width:w*.3,height:h*.64};
   ctx.fillStyle='#170d2bc2';ctx.fillRect(plot.x,plot.y,plot.width,plot.height);
   ctx.strokeStyle='#6b4c85';ctx.strokeRect(plot.x,plot.y,plot.width,plot.height);
   ctx.fillStyle='#edce9c';ctx.font='11px ui-monospace,monospace';ctx.fillText('RSSI / HISTORY',plot.x+9,plot.y+18);
   const all=rows.filter(a=>Number.isFinite(a.data?.rssi)).slice(-40);
   for(let i=0;i<4;i++){
     const y=plot.y+35+(plot.height-48)*i/3;
     line(plot.x+7,y,plot.x+plot.width-8,y,'#755b9566');
     ctx.fillStyle='#b09bc0';ctx.font='9px ui-monospace,monospace';
     ctx.fillText(String(-20-i*30),plot.x+7,y-3);
   }
   if(all.length){
     ctx.beginPath();
     for(let i=0;i<all.length;i++){
       const x=plot.x+20+i/Math.max(1,all.length-1)*(plot.width-35);
       const val=Math.max(-115,Math.min(-20,all[i].data.rssi));
       const y=plot.y+32+(1-(val+115)/95)*(plot.height-47);
       if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
     }
     ctx.lineWidth=2;ctx.strokeStyle='#edc788';ctx.stroke();
   } else {
     ctx.fillStyle='#aa97c0';ctx.fillText('NO RSSI DATA',plot.x+10,plot.y+plot.height*.5);
   }
   ctx.fillStyle='#d7b77e';ctx.font='9px ui-monospace,monospace';
   ctx.fillText('ABSTRACT SIGNAL MAP',cx-r+5,h-14);
   set('showPulse',rows.length?`SAMPLES ${String(rows.length).padStart(3,'0')} / ${all.length} RSSI`:'AWAITING DATA');
 }
 byId('showEvidence').addEventListener('click',()=>{mode='replay';rows=[];lastFetch=0;updateFacts();loadRecords(true)});
 byId('showDemo').addEventListener('click',()=>{mode='demo';rows=fakeRows();updateFacts()});
 byId('showRefresh').addEventListener('click',()=>{if(mode==='demo'){rows=fakeRows();updateFacts()}else{lastFetch=0;loadRecords(true)}});
 byId('showPause').addEventListener('click',()=>{active=!active;updateFacts()});
 byId('showFullscreen').addEventListener('click',()=>{
   if(document.fullscreenElement)document.exitFullscreen();
   else if(stage.requestFullscreen)stage.requestFullscreen();
 });
 document.addEventListener('fullscreenchange',()=>setTimeout(adjust,100));
 adjust();updateFacts();requestAnimationFrame(draw);loadRecords(true);
})();
