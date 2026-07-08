/* scene.js — 8ビット風景（奥）と桜の枝（手前）・花びらをページに注入する。
   通信なし・データ収集なし。純粋な装飾スクリプト。 */
(function(){
  "use strict";
  var d=document;

  var SCENE='<div class="px-scene" aria-hidden="true">'+
  '<svg viewBox="0 0 480 300" preserveAspectRatio="xMidYMax slice" shape-rendering="crispEdges">'+
  '<rect x="0" y="0" width="480" height="70" fill="#bfe2f5"/>'+
  '<rect x="0" y="70" width="480" height="55" fill="#cdeaf8"/>'+
  '<rect x="0" y="125" width="480" height="55" fill="#ddf1fa"/>'+
  '<rect x="0" y="180" width="480" height="40" fill="#eaf6fc"/>'+
  '<circle cx="404" cy="52" r="17" fill="#ffedb0"/>'+
  '<g fill="#ffffff"><rect x="140" y="46" width="44" height="7"/><rect x="152" y="39" width="24" height="7"/>'+
  '<rect x="300" y="70" width="36" height="7"/><rect x="308" y="63" width="20" height="7"/>'+
  '<rect x="50" y="96" width="30" height="6"/></g>'+
  '<polygon points="0,208 90,168 190,208 290,164 380,204 480,172 480,300 0,300" fill="#a9d9a4"/>'+
  '<polygon points="228,120 252,120 266,152 282,188 306,224 174,224 198,188 214,152" fill="#9aa6cf"/>'+
  '<polygon points="228,120 252,120 261,140 255,148 250,140 245,149 240,141 235,149 230,140 224,148 219,140" fill="#f6f8ff"/>'+
  '<polygon points="0,238 120,210 240,244 340,214 480,240 480,300 0,300" fill="#7fc283"/>'+
  '<g fill="#f5b5d2"><rect x="66" y="192" width="16" height="12"/><rect x="58" y="197" width="32" height="10"/></g>'+
  '<rect x="71" y="204" width="6" height="10" fill="#8a6a4a"/>'+
  '<g fill="#f8c6dc"><rect x="352" y="196" width="16" height="12"/><rect x="344" y="201" width="32" height="10"/></g>'+
  '<rect x="357" y="208" width="6" height="10" fill="#8a6a4a"/>'+
  '<g fill="#f6b6d2"><rect x="180" y="80" width="5" height="5"/><rect x="220" y="140" width="5" height="5"/>'+
  '<rect x="330" y="110" width="5" height="5"/><rect x="410" y="150" width="5" height="5"/>'+
  '<rect x="150" y="170" width="5" height="5"/><rect x="270" y="95" width="5" height="5"/>'+
  '<rect x="450" y="100" width="5" height="5"/><rect x="120" y="130" width="5" height="5"/>'+
  '<rect x="380" y="86" width="5" height="5"/><rect x="60" y="150" width="5" height="5"/></g>'+
  '</svg></div>';

  var FG='<div class="px-fg" aria-hidden="true">'+
  '<svg viewBox="0 0 1000 200" preserveAspectRatio="xMaxYMin slice" shape-rendering="crispEdges"><g transform="translate(1000 0) scale(-1 1)">'+
  '<path d="M150,-6 Q230,26 340,40 Q450,54 540,44" stroke="#7a5a38" stroke-width="11" fill="none"/>'+
  '<path d="M240,28 Q256,48 264,64 M380,46 Q396,64 402,82" stroke="#7a5a38" stroke-width="6" fill="none"/>'+
  '<g fill="#f78fbd"><circle cx="262" cy="64" r="9"/><circle cx="275" cy="71" r="9"/><circle cx="267" cy="81" r="9"/><circle cx="254" cy="74" r="9"/></g><circle cx="265" cy="73" r="4" fill="#ffd94a"/>'+
  '<g fill="#fba9cd"><circle cx="318" cy="26" r="9"/><circle cx="331" cy="33" r="9"/><circle cx="323" cy="43" r="9"/><circle cx="310" cy="36" r="9"/></g><circle cx="321" cy="35" r="4" fill="#ffd94a"/>'+
  '<g fill="#f78fbd"><circle cx="402" cy="82" r="9"/><circle cx="415" cy="89" r="9"/><circle cx="407" cy="99" r="9"/><circle cx="394" cy="92" r="9"/></g><circle cx="405" cy="91" r="4" fill="#ffd94a"/>'+
  '<g fill="#fba9cd"><circle cx="462" cy="42" r="8"/><circle cx="474" cy="48" r="8"/><circle cx="467" cy="57" r="8"/><circle cx="455" cy="51" r="8"/></g><circle cx="465" cy="50" r="3.5" fill="#ffd94a"/>'+
    '<g fill="#fba9cd"><circle cx="196" cy="8" r="9"/><circle cx="209" cy="15" r="9"/><circle cx="201" cy="25" r="9"/><circle cx="188" cy="18" r="9"/></g><circle cx="199" cy="17" r="4" fill="#ffd94a"/>'+
  '</g></svg></div>';

  function inject(){
    var t=d.createElement("div");
    t.innerHTML=SCENE+FG;
    while(t.firstElementChild) d.body.appendChild(t.firstElementChild);
    var petals=[[22,11,0],[38,14,3],[55,12,6],[70,15,1.5],[84,13,8],[47,16,10]];
    petals.forEach(function(p){
      var e=d.createElement("div");
      e.className="px-petal";
      e.style.left=p[0]+"%";
      e.style.animationDuration=p[1]+"s";
      e.style.animationDelay=p[2]+"s";
      d.body.appendChild(e);
    });
  }
  if(d.readyState==="loading") d.addEventListener("DOMContentLoaded",inject);
  else inject();
})();
