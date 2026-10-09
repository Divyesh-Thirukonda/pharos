import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {Activity,ArrowUpRight,CheckCircle2,Clock,Eye,Info,LoaderCircle,MapPin,Pause,Radio,ScanLine,Video,X} from 'lucide-react';
import {clockTime,isPending,mediaUrl,visionApi,type LiveCamera,type VisionJob} from './vision';

function usePageVisible(){const [visible,setVisible]=useState(document.visibilityState==='visible');useEffect(()=>{const onChange=()=>setVisible(document.visibilityState==='visible');document.addEventListener('visibilitychange',onChange);return()=>document.removeEventListener('visibilitychange',onChange);},[]);return visible;}

function LivePlayer({camera}:{camera:LiveCamera}){
 const ref=useRef<HTMLVideoElement>(null),[status,setStatus]=useState<'connecting'|'playing'|'paused'|'unavailable'>('connecting');
 useEffect(()=>{let disposed=false;let destroy:(()=>void)|undefined;const video=ref.current!;
  const connect=async()=>{try{if(video.canPlayType('application/vnd.apple.mpegurl')){video.src=camera.streamUrl;void video.play().catch(()=>setStatus('paused'));}else{const {default:Hls}=await import('hls.js');if(disposed)return;if(!Hls.isSupported()){setStatus('unavailable');return;}const hls=new Hls({liveSyncDurationCount:3,maxBufferLength:15});destroy=()=>hls.destroy();hls.on(Hls.Events.ERROR,(_event,data)=>{if(data.fatal)setStatus('unavailable');});hls.on(Hls.Events.MANIFEST_PARSED,()=>{void video.play().catch(()=>setStatus('paused'));});hls.loadSource(camera.streamUrl);hls.attachMedia(video);}}catch{if(!disposed)setStatus('unavailable');}};
  void connect();let resume=false;const visibility=()=>{if(document.hidden){resume=!video.paused;video.pause();}else if(resume)void video.play().catch(()=>{});};document.addEventListener('visibilitychange',visibility);
  return()=>{disposed=true;destroy?.();video.pause();video.removeAttribute('src');video.load();document.removeEventListener('visibilitychange',visibility);};
 },[camera.id,camera.streamUrl]);
 return <div className="live-player"><div className="player-heading"><span className={`live-state ${status==='playing'?'is-playing':''}`}><Radio size={12}/>{status==='playing'?'LIVE SOURCE':status==='connecting'?'CONNECTING':status==='paused'?'SOURCE PAUSED':'SOURCE UNAVAILABLE'}</span><a href={camera.sourceUrl} target="_blank" rel="noreferrer">511NY<ArrowUpRight size={11}/></a></div><video ref={ref} autoPlay muted playsInline controls onPlaying={()=>setStatus('playing')} onPause={()=>setStatus(s=>s==='unavailable'?s:'paused')} onError={()=>setStatus('unavailable')} aria-label={`Live roadway video at ${camera.name}`}/>{status==='connecting'?<div className="live-connecting"><LoaderCircle size={18} className="spin"/>Connecting to the camera</div>:null}{status==='unavailable'?<p className="observation-error">Live playback is unavailable. You can still try a captured review.</p>:null}<p className="live-source-note">Live source · a short broadcast delay is possible.</p></div>;
}

export function CapturedVideo({job}:{job:VisionJob}){
 const [time,setTime]=useState(0),[overlay,setOverlay]=useState(true),[forecast,setForecast]=useState(false),[failed,setFailed]=useState(false);const video=useRef<HTMLVideoElement>(null);
 const frames=job.detections?.frames??[];
 const frame=useMemo(()=>{let nearest=frames[0];for(const candidate of frames){if(candidate.timeSec<=time+.025)nearest=candidate;else break;}return nearest&&Math.abs(nearest.timeSec-time)<.45?nearest:undefined;},[frames,time]);
 const normalized=job.tracking?.tracks??[];
 const canProject=job.source?.sourceKind==='live_video'&&normalized.some(track=>track.forecasts.length>0);
 const showProjection=forecast&&canProject;
 const currentTracks=normalized.map(track=>({track,current:track.observations.find(o=>o.frameIndex===frame?.frameIndex),forecast:track.forecasts.find(f=>f.frameIndex===frame?.frameIndex),trail:track.observations.filter(o=>o.timeSec<=time+.025&&o.timeSec>=time-2)})).filter(t=>t.current);
 const overlap=job.tracking?.potentialConflicts.filter(c=>c.frameIndex===frame?.frameIndex)??[];
 const box=(b:number[],normalizedBox=false)=>{const width=normalizedBox?1:(frame?.shape[1]??job.video?.width??1),height=normalizedBox?1:(frame?.shape[0]??job.video?.height??1);return{x:100*b[0]/width,y:100*b[1]/height,width:100*(b[2]-b[0])/width,height:100*(b[3]-b[1])/height};};
 return <div className="captured-evidence">
  <div className="player-heading"><span><Video size={12}/>CAPTURE REPLAY</span><span>{job.video?.durationSec?.toFixed(1)??'—'}s</span></div>
  <div className="capture-canvas" style={{aspectRatio:job.video?`${job.video.width}/${job.video.height}`:'16/9'}}>
   <video key={job.id} ref={video} src={job.mediaUrl?mediaUrl(job.mediaUrl):undefined} controls muted playsInline preload="metadata" onTimeUpdate={e=>setTime(e.currentTarget.currentTime)} onSeeked={e=>setTime(e.currentTarget.currentTime)} onError={()=>setFailed(true)} aria-label="Captured source footage analyzed by the models"/>
   {overlay&&frame?<svg viewBox="0 0 100 100" preserveAspectRatio="none" className="detection-overlay" aria-label="Observed object boxes at this captured frame">
    {frame.detections.map((d,i)=><g key={i}><rect {...box(d.bbox)} fill="none" stroke={d.label==='person'?'#ade7cb':'#f4c786'} strokeWidth=".35"/><text x={box(d.bbox).x+.25} y={Math.max(2,box(d.bbox).y-.8)} fontSize="2.2" fill="#ffffff" stroke="#102b28" strokeWidth=".15" paintOrder="stroke">{d.label}</text></g>)}
    {currentTracks.map(({track,trail,forecast:projection})=><g key={track.trackId}><polyline points={trail.map(o=>o.footpoint.map(v=>v*100).join(',')).join(' ')} fill="none" stroke="#a1e2d1" strokeWidth=".5"/>{showProjection&&projection?<polyline points={projection.points.map(p=>p.map(v=>v*100).join(',')).join(' ')} fill="none" stroke="#f4c786" strokeWidth=".6" strokeDasharray="1.4 1"/>:null}</g>)}
    {showProjection?overlap.map((c,i)=><rect key={i} {...box(c.overlapBox,true)} fill="#e68e69" fillOpacity=".25" stroke="#ffa283" strokeWidth=".7" strokeDasharray="1 1"/>):null}
   </svg>:null}
  </div>
  {failed?<p className="observation-error">The analyzed capture could not be played.</p>:null}
  <div className="overlay-controls"><button aria-pressed={overlay} className={overlay?'enabled':''} onClick={()=>setOverlay(!overlay)}><ScanLine size={13}/>Object boxes</button>{canProject?<button aria-pressed={showProjection} className={forecast?'enabled':''} onClick={()=>{setForecast(!forecast);setOverlay(true);}}><Activity size={13}/>Replay projection</button>:null}<span>{time.toFixed(1)} / {job.video?.durationSec?.toFixed(1)??'—'}s</span></div>
  {showProjection?<p className="projection-note">Up to 2s projected from replay +{(frame?.timeSec??time).toFixed(1)}s · not a live warning.</p>:null}
  {showProjection&&overlap.length?<p className="projection-alert">Potential image overlap · {overlap.length} {overlap.length===1?'pair':'pairs'} to review at +{(frame?.timeSec??time).toFixed(1)}s.</p>:null}
  <div className="capture-timestamps"><span><Clock size={11}/>{job.source?.sourceKind==='recorded_video'?'Excerpt prepared':'Window received'} {clockTime(job.captureStartedAt)} – {clockTime(job.captureEndedAt)} ET</span>{job.completedAt?<span>Reviewed {clockTime(job.completedAt)} ET</span>:null}</div>
  <details className="analysis-limits capture-details"><summary>Capture details</summary>
   <p className="capture-models">{job.models?.yolo??'YOLO'} object detections. Boxes show model estimates; frame detections are not counts of unique people or events.</p>
   {job.source?.sourceKind==='recorded_video'?<p>The original recording time is unverified. The timestamp above is when this excerpt was prepared.</p>:<p>The source clock and broadcast delay are unverified. This replay describes the received window, not the street now.</p>}
   {canProject?<p>Dashed lines extend recent motion within the image. Perspective and occlusion can create apparent overlap; projections do not confirm a near miss. Calibrated road speed and time to collision are unavailable.</p>:null}
   {job.tracking?.limitations?.length?<ul>{job.tracking.limitations.map((limit,i)=><li key={i}>{limit}</li>)}</ul>:null}
  </details>
 </div>;
}

export function VisionAnalysis({cameraId,evidenceId,query,autoStart=false,allowMonitor=false}:{cameraId?:string;evidenceId?:string;query:string;autoStart?:boolean;allowMonitor?:boolean}){
 const [job,setJob]=useState<VisionJob|null>(null),[lastComplete,setLastComplete]=useState<VisionJob|null>(null),[submitting,setSubmitting]=useState(false),[error,setError]=useState<string|null>(null),[monitor,setMonitor]=useState(allowMonitor),[now,setNow]=useState(Date.now());
 const visible=usePageVisible(),alive=useRef(true),inFlight=useRef(false),autoStarted=useRef(false),lastStarted=useRef(0),pollFailures=useRef(0);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 useEffect(()=>{if(!visible)return;setNow(Date.now());const timer=setInterval(()=>setNow(Date.now()),5000);return()=>clearInterval(timer);},[visible]);
 const start=useCallback(async()=>{if(inFlight.current||document.hidden)return;if(!query.trim()){setError('Enter a question to check against the captured footage.');return;}inFlight.current=true;lastStarted.current=Date.now();setSubmitting(true);setError(null);pollFailures.current=0;try{const created=await visionApi<VisionJob>('jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...(cameraId?{cameraId}:{evidenceId}),query})});if(alive.current)setJob(created);}catch(e){if(alive.current)setError(e instanceof Error?e.message:'Analysis could not start.');inFlight.current=false;}finally{if(alive.current)setSubmitting(false);}},[cameraId,evidenceId,query]);
 useEffect(()=>{if(autoStart&&visible&&!autoStarted.current){autoStarted.current=true;void start();}},[autoStart,visible,start]);
 useEffect(()=>{if(!job||!isPending(job)||!visible)return;const timer=setTimeout(async()=>{try{const updated=await visionApi<VisionJob>(`jobs/${encodeURIComponent(job.id)}`);if(!alive.current)return;pollFailures.current=0;setJob(updated);if(updated.status==='completed')setLastComplete(updated);if(!isPending(updated))inFlight.current=false;}catch(e){if(!alive.current)return;pollFailures.current+=1;if(pollFailures.current>=3){inFlight.current=false;setError('The analysis connection was lost. Start a new captured window to try again.');setJob({...job,status:'failed'});}else setJob({...job});}},2000);return()=>clearTimeout(timer);},[job,visible]);
 const pending=submitting||isPending(job);
 useEffect(()=>{if(!monitor||!visible||pending)return;const timer=setTimeout(()=>void start(),Math.max(30000-(Date.now()-lastStarted.current),1000));return()=>clearTimeout(timer);},[monitor,visible,pending,start,job,error]);
 const displayed=job?.status==='completed'||job?.status==='failed'||!lastComplete?job:lastComplete;
 const verdict=displayed?.analysis?.verdict;
 const secondsSince=(value?:string)=>{if(!value)return null;const stamp=new Date(value).getTime();return Number.isFinite(stamp)?Math.max(0,Math.floor((now-stamp)/1000)):null;};
 const age=secondsSince(displayed?.completedAt),captureAge=secondsSince(displayed?.captureEndedAt);
 const elapsed=(seconds:number)=>seconds<60?`${seconds}s`:`${Math.floor(seconds/60)}m ${seconds%60}s`;
 return <section className="vision-analysis" aria-label="Analysis of captured footage">
  <div className="observer-section-title"><div><span className="eyebrow">FOOTAGE REVIEW</span><h3>{cameraId?'Latest observation':'Review this moment'}</h3></div>{allowMonitor?<button className={`monitor-switch ${monitor?'enabled':''}`} aria-pressed={monitor} onClick={()=>setMonitor(!monitor)}>{monitor?<Pause size={12}/>:<Radio size={12}/>}Monitor {monitor?'on':'off'}</button>:null}</div>
  <div className="analysis-controls"><button className="primary-button" disabled={pending||!visible} onClick={()=>void start()}>{pending?<LoaderCircle size={14} className="spin"/>:<ScanLine size={14}/>} {pending?job?.status==='capturing'?'Capturing footage…':'Reviewing footage…':job?'Review another window':cameraId?'Review camera footage':'Review this footage'}</button>{pending?<span className="job-status" role="status">{job?.status==='queued'?'Queued':job?.status==='capturing'?'Capturing':'Analyzing'}</span>:null}</div>
  {monitor?<p className="monitor-note">{!visible?'Monitoring paused while this page is hidden.':'Monitoring every 30s, once each review finishes.'}</p>:null}
  {error?<p className="observation-error" role="alert">{error}</p>:null}
  {pending&&lastComplete?<p className="monitor-note">Updating. The previous capture remains below.</p>:null}
  {displayed?.mediaUrl?<CapturedVideo key={displayed.id} job={displayed}/>:null}
  {displayed?.analysis?<div className={`query-verdict verdict-${verdict}`}>
   <span>{verdict==='supported'?<CheckCircle2 size={16}/>:verdict==='not_observed'?<Eye size={16}/>:<Info size={16}/>}<strong>{verdict==='supported'?'AI-supported observation':verdict==='not_observed'?'Requested event not observed':'Uncertain · needs review'}</strong></span>
   {displayed.query?<p className="checked-query">Question: {displayed.query}</p>:null}
   <p>{displayed.analysis.summary}</p>
   {captureAge!==null?<small>{displayed.source?.sourceKind==='recorded_video'?'Excerpt prepared':'Window received'} {elapsed(captureAge)} ago{age!==null?` · reviewed ${elapsed(age)} ago`:''}</small>:age!==null?<small>Reviewed {elapsed(age)} ago · capture time unavailable.</small>:null}
   {displayed.analysis.observations?.length?<ul>{displayed.analysis.observations.map((o,i)=><li key={i}>{o.startSec!==null?<span className="observation-time">{o.startSec.toFixed(1)}{o.endSec!==null?`–${o.endSec.toFixed(1)}`:''}s</span>:null}{o.detail}</li>)}</ul>:null}
  </div>:null}
  {displayed?.cosmosObservation?<details className="cosmos-evidence" open={!displayed.analysis}><summary><ScanLine size={13}/>Cosmos scene observation</summary><p>{displayed.cosmosObservation}</p><small>{displayed.models?.cosmos??'NVIDIA Cosmos'} · verify against the capture.</small></details>:null}
  {displayed?.analysis?.nextSteps?.length?<div className="observer-next-steps"><span className="eyebrow">NEXT STEPS</span>{displayed.analysis.nextSteps.map((step,i)=><article key={i}><h4>{step.title}</h4><p>{step.detail}</p>{step.sourceUrl?<a href={step.sourceUrl} target="_blank" rel="noreferrer">Source guidance<ArrowUpRight size={11}/></a>:null}</article>)}</div>:null}
  {displayed?.analysis?<details className="analysis-limits"><summary>How to read this review</summary><p>This AI review checks the complete question against this capture. A supported observation is not a confirmed near-miss count; “not observed” does not establish that an event never occurred.</p>{displayed.analysis.limitations?.length?<ul>{displayed.analysis.limitations.map((limit,i)=><li key={i}>{limit}</li>)}</ul>:null}<p>NVIDIA Cosmos describes the footage, object detection supplies boxes, and the review checks the question against the source. {displayed.models?.assessment?`Review model: ${displayed.models.assessment}.`:''}</p></details>:null}
  {displayed?.errors?.length?<details className="partial-results"><summary>Some analysis is unavailable</summary>{displayed.errors.map((e,i)=><p key={i}>{e.stage}: {e.message}</p>)}</details>:null}
  {job?.status==='failed'&&!error?<p className="observation-error">This review did not complete. Partial results are shown above.</p>:null}
 </section>;
}

export default function LiveObserver({camera,onClose,embedded=false}:{camera:LiveCamera;onClose?:()=>void;embedded?:boolean}){
 const [question,setQuestion]=useState('Look for visible close passes, failure to yield, or abrupt evasive action.');
 const Container=embedded?'section':'aside';
 return <Container className={embedded?'live-observer-embedded':'detail-panel live-detail'} aria-label={`Live observation at ${camera.name}`}>
  {!embedded?<div className="detail-header"><div className="eyebrow"><Radio size={12}/>LIVE CAMERA</div>{onClose?<button className="icon-button" onClick={onClose} aria-label="Close live camera"><X size={18}/></button>:null}</div>:null}
  <h2>{camera.name}</h2>
  <div className="detail-subtitle"><MapPin size={12}/>Manhattan · 511NY / NYSDOT</div>
  <div className={embedded?'live-observer-content':'detail-body'}>
   <LivePlayer key={camera.id} camera={camera}/>
   <label className="observer-query"><span>What should PharOS look for?</span><textarea value={question} maxLength={1200} onChange={e=>setQuestion(e.target.value)} rows={3}/></label>
   <VisionAnalysis key={camera.id} cameraId={camera.id} query={question} autoStart allowMonitor/>
  </div>
 </Container>;
}
