import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';
const mainUrl=new URL(window.location.href);
if(mainUrl.searchParams.has('v')){mainUrl.searchParams.delete('v');window.history.replaceState(window.history.state,'',mainUrl.pathname+mainUrl.search+mainUrl.hash);}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
