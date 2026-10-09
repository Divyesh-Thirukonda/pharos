import {forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import * as maplibregl from 'maplibre-gl';
import type {ExpressionSpecification,GeoJSONSource,Map as MapInstance,StyleSpecification} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type {Camera,Intersection} from './types';
import type {LiveCamera} from './vision';

maplibregl.setWorkerUrl(workerUrl);
export type CityMapHandle={home:()=>void;overview:()=>void;zoom:(by:number)=>void;toggle3d:()=>void;fly:(point:{lon:number;lat:number},street?:boolean)=>void};
type Props={intersections:Intersection[];cameras:Camera[];selected:{lat:number;lon:number}|null;liveCameras:LiveCamera[];showLive:boolean;heat:boolean;showCameras:boolean;onSelect:(id:string)=>void;onCamera:(id:string)=>void;onLiveCamera:(id:string)=>void;onReady:()=>void};
const empty={type:'FeatureCollection' as const,features:[]};
// The home coordinates are the NYC DOT registry's 6 Ave @ 23 St camera location.
const initial={center:[-73.992797766009,40.7429025573452] as [number,number],zoom:14.6,pitch:62,bearing:-28};
const reduced=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const framePadding=(m?:MapInstance)=>({left:0,right:window.innerWidth<=760?0:430,top:0,bottom:window.innerWidth<=760?Math.round((m?.getContainer().clientHeight??window.innerHeight)*.56):0});
// One ramp for the heat layer and the dots, keyed to real injury-crash counts (the busiest corner has about 17).
const RAMP=['#f2d16b','#f0a23a','#dc2f2f','#9b1020','#520a16'] as const;
const historyColor:ExpressionSpecification=['interpolate',['linear'],['get','weight'],1,RAMP[0],4,RAMP[1],8,RAMP[2],12,RAMP[3],17,RAMP[4]];
const pointData=(items:Array<{id:string;lon:number;lat:number;name:string}>,kind:string)=>({type:'FeatureCollection' as const,features:items.map(item=>({type:'Feature' as const,geometry:{type:'Point' as const,coordinates:[item.lon,item.lat]},properties:{id:item.id,name:item.name,kind}}))});

function pharosStyle(style:StyleSpecification){
 for(const layer of style.layers){
  const id=layer.id;
  if(layer.type==='background')layer.paint={...layer.paint,'background-color':'#e9ede6'};
  if(layer.type==='fill'){
   if(/water/.test(id))layer.paint={...layer.paint,'fill-color':'#b8cfd0'};
   else if(/park|wood|grass|cemetery/.test(id))layer.paint={...layer.paint,'fill-color':'#c5d2bd','fill-outline-color':'#b7c8b0'};
   else if(/landuse|landcover/.test(id))layer.paint={...layer.paint,'fill-color':'#e5e9df'};
   else if(id==='building')layer.paint={...layer.paint,'fill-color':'#dce2d9','fill-outline-color':'#c5d0c7'};
  }
  if(layer.type==='line'){
   if(/waterway/.test(id))layer.paint={...layer.paint,'line-color':'#b8cfd0'};
   else if(/park/.test(id))layer.paint={...layer.paint,'line-color':'#afc1a7'};
   else if(/road|bridge|tunnel/.test(id)&&!/rail/.test(id))layer.paint={...layer.paint,'line-color':/casing/.test(id)?'#d1d6c9':/motorway|trunk_primary/.test(id)?'#f4ead4':'#fffdf6'};
  }
  if(layer.type==='fill-extrusion'){
   // Preserve Liberty's actual building footprints/heights and a single 3D layer.
   layer.paint={...layer.paint,'fill-extrusion-color':['interpolate',['linear'],['coalesce',['get','render_height'],12],0,'#eeeee5',70,'#dce2d9',180,'#c4d3cd',350,'#a6bfba'],'fill-extrusion-opacity':.92};
  }
  if(layer.type==='symbol'){
   if(/poi_r|highway-shield|road_shield/.test(id))layer.layout={...layer.layout,visibility:'none'};
   if(layer.layout?.['text-field'])layer.paint={...layer.paint,'text-color':/water/.test(id)?'#557b7c':'#61736a','text-halo-color':'#f8faf3','text-halo-width':1.3};
  }
 }
 return style;
}

const CityMap=forwardRef<CityMapHandle,Props>(function CityMap(props,ref){
 const element=useRef<HTMLDivElement>(null),map=useRef<MapInstance|null>(null),callbacks=useRef(props);
 callbacks.current=props;
 const [error,setError]=useState(false),[loaded,setLoaded]=useState(false);
 useImperativeHandle(ref,()=>({
  home(){const m=map.current;m?.easeTo({...initial,padding:framePadding(m),duration:reduced()?0:1100});},
  overview(){const m=map.current;if(!m)return;const p=framePadding(m);m.fitBounds([[-74.025,40.695],[-73.905,40.878]],{padding:{left:p.left+36,right:p.right+36,top:p.top+36,bottom:p.bottom+36},pitch:30,bearing:-28,duration:reduced()?0:1200});},
  zoom(by){const m=map.current;m?.zoomTo(m.getZoom()+by,{duration:reduced()?0:300});},
  toggle3d(){const m=map.current;if(m)m.easeTo({pitch:m.getPitch()>20?0:62,bearing:m.getPitch()>20?0:-28,padding:framePadding(m),duration:reduced()?0:600});},
  fly(point,street=false){const m=map.current;m?.flyTo({center:[point.lon,point.lat],zoom:street?17.5:17.1,pitch:street?68:62,bearing:-28,padding:framePadding(m),duration:reduced()?0:1300});}
 }),[]);

 useEffect(()=>{
  if(!element.current)return;
  let disposed=false,current:MapInstance|undefined;
  const controller=new AbortController();
  const resize=()=>{if(current&&!disposed)current.setPadding(framePadding(current));};
  void(async()=>{try{
   const response=await fetch('https://tiles.openfreemap.org/styles/liberty',{signal:controller.signal});
   if(!response.ok)throw new Error('Map style unavailable');
   const style=pharosStyle(await response.json() as StyleSpecification);
   if(disposed)return;
   current=new maplibregl.Map({container:element.current!,style,...initial,maxPitch:80,minZoom:10,maxZoom:19,attributionControl:false,canvasContextAttributes:{antialias:true}});
   map.current=current;
   current.setPadding(framePadding(current));
   current.addControl(new maplibregl.NavigationControl({visualizePitch:true}),'top-right');
   current.addControl(new maplibregl.AttributionControl({compact:true}),'bottom-right');
   current.on('resize',resize);
   current.on('load',()=>{
    if(disposed)return;
    const m=current!;
    m.setLight({anchor:'map',color:'#fff9eb',intensity:.45,position:[1.4,140,35]});
    for(const id of ['hotspots','cameras','selected','live-cameras'])m.addSource(id,{type:'geojson',data:empty});
    // Historical crash/injury records only. Camera availability never changes this heat layer.
    m.addLayer({id:'hotspot-heat',type:'heatmap',source:'hotspots',paint:{'heatmap-weight':['interpolate',['linear'],['get','weight'],0,0,1,.18,4,.4,8,.65,17,1],'heatmap-intensity':['interpolate',['linear'],['zoom'],11,1.2,14,1.9,17,2.8],'heatmap-radius':['interpolate',['linear'],['zoom'],11,22,13,34,15,50,17,80],'heatmap-opacity':.86,'heatmap-color':['interpolate',['linear'],['heatmap-density'],0,'rgba(242,209,107,0)',.12,'rgba(242,209,107,.5)',.32,'rgba(240,162,58,.78)',.55,'rgba(220,47,47,.88)',.78,'rgba(155,16,32,.94)',1,'rgba(82,10,22,.97)']}});
    m.addLayer({id:'hotspot-halo',type:'circle',source:'hotspots',paint:{'circle-radius':['interpolate',['linear'],['get','weight'],1,14,17,34],'circle-color':historyColor,'circle-opacity':.4,'circle-blur':.45}});
    m.addLayer({id:'hotspot-points',type:'circle',source:'hotspots',paint:{'circle-radius':['interpolate',['linear'],['get','weight'],1,4,17,10],'circle-color':historyColor,'circle-stroke-width':2,'circle-stroke-color':'#fffdf6'}});
    m.addLayer({id:'camera-halo',type:'circle',source:'cameras',paint:{'circle-radius':11,'circle-color':'#527f75','circle-opacity':.14,'circle-blur':.6}});
    m.addLayer({id:'camera-points',type:'circle',source:'cameras',paint:{'circle-radius':['interpolate',['linear'],['zoom'],11,3.5,15,5,18,6],'circle-color':'#fafbf6','circle-stroke-width':2,'circle-stroke-color':'#527f75'}});
    m.addLayer({id:'live-camera-halo',type:'circle',source:'live-cameras',paint:{'circle-radius':19,'circle-color':'#216b65','circle-opacity':.24,'circle-blur':.5}});
    m.addLayer({id:'live-camera-points',type:'circle',source:'live-cameras',paint:{'circle-radius':7,'circle-color':'#216b65','circle-stroke-width':2.5,'circle-stroke-color':'#fffdf6'}});
    for(const [id,source] of [['hotspot-hit','hotspots'],['camera-hit','cameras'],['live-camera-hit','live-cameras']])m.addLayer({id,type:'circle',source,paint:{'circle-radius':13,'circle-opacity':0}});
    for(const [id,source,minzoom] of [['camera-labels','cameras',15.5],['live-camera-labels','live-cameras',14]] as const)m.addLayer({id,type:'symbol',source,minzoom,layout:{'text-field':['concat',['get','name'],'\n',['get','kind']],'text-size':11,'text-offset':[0,1.5],'text-anchor':'top','text-font':['Noto Sans Regular'],'text-max-width':16},paint:{'text-color':'#183738','text-halo-color':'#fffdf6','text-halo-width':1.5}});
    m.addLayer({id:'selected-ring',type:'circle',source:'selected',paint:{'circle-radius':20,'circle-color':'#d2a158','circle-opacity':.08,'circle-stroke-width':3,'circle-stroke-color':'#b9823e'}});
    const pick=(point:maplibregl.Point)=>{
     const layers=['live-camera-hit','camera-hit','hotspot-hit'];
     const features=m.queryRenderedFeatures([[point.x-4,point.y-4],[point.x+4,point.y+4]],{layers});
     return layers.map(layer=>features.find(feature=>feature.layer.id===layer)).find(Boolean);
    };
    m.on('click',e=>{const feature=pick(e.point),id=feature?.properties?.id;if(!id)return;if(feature.layer.id==='live-camera-hit')callbacks.current.onLiveCamera(id);else if(feature.layer.id==='camera-hit')callbacks.current.onCamera(id);else callbacks.current.onSelect(id);});
    m.on('mousemove',e=>{m.getCanvas().style.cursor=pick(e.point)?'pointer':'';});
    m.getCanvas().addEventListener('mouseleave',()=>{m.getCanvas().style.cursor='';});
    setLoaded(true);callbacks.current.onReady();
   });
   current.on('error',event=>{if(!disposed&&!current?.isStyleLoaded()&&event.error?.message?.includes('WebGL'))setError(true);});
  }catch{if(!disposed)setError(true);}})();
  return()=>{disposed=true;controller.abort();current?.remove();map.current=null;};
 },[]);
 useEffect(()=>{
  if(!loaded)return;
  (map.current!.getSource('hotspots') as GeoJSONSource).setData({type:'FeatureCollection',features:props.intersections.map(item=>({type:'Feature',geometry:{type:'Point',coordinates:[item.lon,item.lat]},properties:{id:item.id,name:item.name,weight:item.injuryCrashes??item.injuries}}))});
 },[loaded,props.intersections]);
 useEffect(()=>{if(loaded)(map.current!.getSource('cameras') as GeoJSONSource).setData(pointData(props.cameras,'Latest still'));},[loaded,props.cameras]);
 useEffect(()=>{if(loaded)(map.current!.getSource('live-cameras') as GeoJSONSource).setData(pointData(props.liveCameras,'Live video'));},[loaded,props.liveCameras]);
 useEffect(()=>{if(loaded)for(const id of ['live-camera-halo','live-camera-points','live-camera-hit','live-camera-labels'])map.current!.setLayoutProperty(id,'visibility',props.showLive?'visible':'none');},[loaded,props.showLive]);
 useEffect(()=>{
  if(!loaded)return;
  const m=map.current!;
  for(const id of ['hotspot-heat','hotspot-halo','hotspot-points','hotspot-hit'])m.setLayoutProperty(id,'visibility',props.heat?'visible':'none');
  for(const id of ['camera-halo','camera-points','camera-hit','camera-labels'])m.setLayoutProperty(id,'visibility',props.showCameras?'visible':'none');
 },[loaded,props.heat,props.showCameras]);
 useEffect(()=>{if(loaded)(map.current!.getSource('selected') as GeoJSONSource).setData(props.selected?{type:'FeatureCollection',features:[{type:'Feature',geometry:{type:'Point',coordinates:[props.selected.lon,props.selected.lat]},properties:{}}]}:empty);},[loaded,props.selected]);
 return <><div className="city-map" ref={element} role="region" aria-label="Interactive 3D map of Manhattan. Filled teal nodes are live video; outlined nodes are latest stills. Use the right panel camera list for keyboard navigation."/>{error?<div className="map-error"><strong>The city view is unavailable</strong><p>You can still explore cameras, crash history, and footage using the right panel.</p></div>:null}</>;
});
export default CityMap;
