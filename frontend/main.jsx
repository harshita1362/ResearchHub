import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import "./styles.css";

const API=import.meta.env.VITE_API_URL||"http://localhost:8000";
const wsBase=API.replace(/^http/,"ws");
const getToken=()=>localStorage.getItem("rh_token");

async function api(path,opts={}){
  const headers={...(opts.headers||{}),...(getToken()?{Authorization:"Bearer "+getToken()}: {})};
  const r=await fetch(API+path,{...opts,headers});
  const d=await r.json().catch(()=>({}));
  if(!r.ok) throw Error(d.detail||"Request failed");
  return d;
}

function App(){
 const [user,setUser]=useState(JSON.parse(localStorage.getItem("rh_user")||"null"));
 const [view,setView]=useState("home");
 const [services,setServices]=useState([]);
 const [projects,setProjects]=useState([]);
 const [selected,setSelected]=useState(null);
 const [auth,setAuth]=useState("login");
 const logout=()=>{localStorage.clear();setUser(null);setView("home")};
 useEffect(()=>{api("/api/services").then(setServices).catch(()=>{})},[]);
 useEffect(()=>{if(user) loadProjects()},[user]);
 async function loadProjects(){try{setProjects(await api("/api/projects"))}catch{}}
 async function authSubmit(e){
  e.preventDefault(); const f=new FormData(e.currentTarget);
  try{
   const d=await api("/api/auth/"+auth,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(auth==="register"?{name:f.get("name"),email:f.get("email"),password:f.get("password"),research_interest:f.get("interest")}:{email:f.get("email"),password:f.get("password")})});
   localStorage.setItem("rh_token",d.token);localStorage.setItem("rh_user",JSON.stringify(d.user));setUser(d.user);setView("dashboard");
  }catch(err){alert(err.message)}
 }
 async function createProject(){
  const title=prompt("Project title"); if(!title)return;
  const description=prompt("Short research brief")||"";
  try{await api("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({title,description})});loadProjects()}catch(e){alert(e.message)}
 }
 async function pay(id){
  if(!user){setView("auth");return}
  try{const d=await api("/api/payments/checkout/"+id,{method:"POST"}); if(d.checkout_url)location.href=d.checkout_url;else alert(d.message)}catch(e){alert(e.message)}
 }
 return <div>
  <header><a className="brand" onClick={()=>setView("home")}><span>R</span> ResearchHub</a><nav><a onClick={()=>setView("services")}>Services</a><a onClick={()=>user?setView("dashboard"):setView("auth")}>Workspace</a><a onClick={()=>user?setView("assistant"):setView("auth")}>AI Assistant</a></nav><div>{user?<><span className="hello">Hi, {user.name.split(" ")[0]}</span><button className="outline" onClick={logout}>Sign out</button></>:<><button className="outline" onClick={()=>{setAuth("login");setView("auth")}}>Sign in</button><button onClick={()=>{setAuth("register");setView("auth")}}>Get Started</button></>}</div></header>
  {view==="home"&&<Home go={setView}/>}
  {view==="services"&&<Services services={services} pay={pay}/>}
  {view==="auth"&&<Auth mode={auth} setMode={setAuth} submit={authSubmit}/>}
  {view==="dashboard"&&<Dashboard projects={projects} create={createProject} open={async p=>{setSelected(await api("/api/projects/"+p.id));setView("project")}}/>}
  {view==="project"&&selected&&<Project p={selected} token={getToken()} api={api} back={()=>{loadProjects();setView("dashboard")}}/>}
  {view==="assistant"&&<Assistant api={api}/>}
 </div>
}

function Home({go}){return <main><section className="hero"><div><small>RESEARCH • COLLABORATION • INTELLIGENCE</small><h1>Turn research ideas into <i>real progress.</i></h1><p>A focused workspace for researchers to discover expertise, manage projects, get technical support and accelerate the journey from question to reproducible result.</p><div className="actions"><button onClick={()=>go("auth")}>Start your research journey →</button><button className="outline" onClick={()=>go("services")}>Explore services</button></div></div><div className="workspace"><div className="workspace-top">Research workspace <b>● Live</b></div><div className="circle">72%</div><h3>Ransomware Classification</h3><p>Project progress</p><div className="bar"><i/></div><div className="numbers"><span><b>5 / 7</b>Milestones</span><span><b>18</b>Files</span><span><b>2</b>Experts</span></div></div></section><section><small>WHY RESEARCHHUB</small><h2>Everything your research workflow needs.</h2><div className="cards"><Card icon="🔬" title="Research Support" text="Methodology, experiments, implementation and analysis support."/><Card icon="🤖" title="AI Research Workspace" text="Structure research questions, experiments and literature with AI assistance."/><Card icon="📈" title="Project Intelligence" text="Track milestones, files and progress in one focused workspace."/></div></section></main>}
function Card({icon,title,text}){return <article className="card"><span className="icon">{icon}</span><h3>{title}</h3><p>{text}</p></article>}
function Services({services,pay}){return <main><small>RESEARCH SERVICES</small><h2>Expert help, when you need it.</h2><p>Focused technical and research support.</p><div className="cards">{services.map(s=><article className="card service" key={s.id}><span className="icon">{s.icon}</span><small>{s.category}</small><h3>{s.title}</h3><p>{s.description}</p><strong>₹{s.price_inr.toLocaleString("en-IN")}</strong><small>{s.duration}</small><button onClick={()=>pay(s.id)}>Book & pay →</button></article>)}</div></main>}
function Auth({mode,setMode,submit}){return <main className="auth"><div className="auth-card"><small>{mode==="login"?"WELCOME BACK":"GET STARTED"}</small><h2>{mode==="login"?"Sign in to ResearchHub":"Create your research profile"}</h2><form onSubmit={submit}>{mode==="register"&&<label>Name<input name="name" required/></label>}<label>Email<input name="email" type="email" required/></label><label>Password<input name="password" type="password" minLength="8" required/></label>{mode==="register"&&<label>Research interest<input name="interest" placeholder="AI, Cybersecurity, Data Science..."/></label>}<button>{mode==="login"?"Sign in →":"Create account →"}</button></form><p>{mode==="login"?"New to ResearchHub?":"Already have an account?"} <a onClick={()=>setMode(mode==="login"?"register":"login")}>{mode==="login"?"Create an account":"Sign in"}</a></p></div></main>}
function Dashboard({projects,create,open}){return <main><div className="sectionline"><div><small>YOUR WORKSPACE</small><h2>Research dashboard</h2></div><button onClick={create}>＋ New project</button></div><div className="cards mini">{["Total projects","Active","Completed"].map((x,i)=><div className="stat" key={x}><b>{i===0?projects.length:i===1?projects.filter(p=>p.status!=="Completed").length:projects.filter(p=>p.status==="Completed").length}</b><span>{x}</span></div>)}</div><div className="cards">{projects.length?projects.map(p=><article className="card" key={p.id}><small>{p.status}</small><h3>{p.title}</h3><p>{p.description||"No research brief yet."}</p><div className="bar"><i style={{width:p.progress+"%"}}/></div><small>{p.progress}% complete</small><button className="outline dark" onClick={()=>open(p)}>Open workspace →</button></article>):<div className="card"><h3>Your research workspace is ready.</h3><p>Create your first project to start tracking your research.</p><button onClick={create}>Create first project</button></div>}</div></main>}
function Project({p,token,api,back}){const [msgs,setMsgs]=useState(p.messages||[]);const [text,setText]=useState("");const [file,setFile]=useState(null);let ws;
 useEffect(()=>{ws=new WebSocket(`${wsBase}/ws/projects/${p.id}?token=${encodeURIComponent(token)}`);ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.type==="message")setMsgs(x=>[...x,m])};return()=>ws&&ws.close()},[]);
 const send=e=>{e.preventDefault();if(ws?.readyState===1&&text.trim()){ws.send(JSON.stringify({text}));setText("")}};
 const upload=async()=>{if(!file)return;const fd=new FormData();fd.append("file",file);await api(`/api/projects/${p.id}/files`,{method:"POST",body:fd});alert("Uploaded");setFile(null)};
 return <main><button className="outline dark" onClick={back}>← Back</button><h2>{p.title}</h2><p>{p.description}</p><div className="two"><div className="card"><h3>Milestones</h3>{p.milestones.map(m=><p key={m.id}>◉ {m.title} — <b>{m.status}</b></p>)}<h3>Files</h3><input type="file" onChange={e=>setFile(e.target.files[0])}/><button onClick={upload}>Upload</button>{p.files.map(f=><div className="file" key={f.id}>📄 {f.filename}</div>)}</div><div className="card"><h3>💬 Live project chat</h3><div className="chat">{msgs.map((m,i)=><div key={i} className="message">{m.text}</div>)}</div><form className="chatform" onSubmit={send}><input value={text} onChange={e=>setText(e.target.value)} placeholder="Write a message..."/><button>Send</button></form></div></div></main>}
function Assistant({api}){const [q,setQ]=useState("");const [a,setA]=useState("");const ask=async e=>{e.preventDefault();try{setA((await api("/api/ai/assist",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:q})})).answer)}catch(e){setA(e.message)}};return <main><small>AI RESEARCH ASSISTANT</small><h2>Your research copilot.</h2><p>Frame questions, plan experiments and structure the next step.</p><div className="assistant card"><form onSubmit={ask}><textarea value={q} onChange={e=>setQ(e.target.value)} placeholder="e.g. Help me design an experiment for ransomware classification..." rows="6"/><button>Ask ResearchHub AI →</button></form>{a&&<div className="answer"><b>ResearchHub AI</b><p>{a}</p></div>}</div></main>}
createRoot(document.getElementById("root")).render(<App/>);
