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

  /* 桜の枝（手前）: 14pxグリッドのドット絵。
     花は十字5ドット＋金の中心＋濃ピンクの影アクセント（16bit風スプライト） */
  function pxFlower(cx,cy,petal,deep){
    var u=14,h=7;
    return '<g fill="'+petal+'">'+
      '<rect x="'+(cx-h)+'" y="'+(cy-h-u)+'" width="'+u+'" height="'+u+'"/>'+
      '<rect x="'+(cx-h)+'" y="'+(cy-h+u)+'" width="'+u+'" height="'+u+'"/>'+
      '<rect x="'+(cx-h-u)+'" y="'+(cy-h)+'" width="'+u+'" height="'+u+'"/>'+
      '<rect x="'+(cx-h+u)+'" y="'+(cy-h)+'" width="'+u+'" height="'+u+'"/>'+
      '</g>'+
      '<g fill="'+deep+'">'+
      '<rect x="'+(cx-h)+'" y="'+(cy+h+h)+'" width="'+u+'" height="'+h+'"/>'+
      '<rect x="'+(cx+h)+'" y="'+(cy-h)+'" width="'+h+'" height="'+u+'"/>'+
      '</g>'+
      '<rect x="'+(cx-h)+'" y="'+(cy-h)+'" width="'+u+'" height="'+u+'" fill="#ffd94a"/>';
  }
  var FG='<div class="px-fg" aria-hidden="true">'+
  '<svg viewBox="0 0 1000 200" preserveAspectRatio="xMaxYMin slice" shape-rendering="crispEdges"><g transform="translate(1000 0) scale(-1 1)">'+
  '<g fill="#7a5a38">'+
  '<rect x="84" y="0" width="154" height="28"/>'+
  '<rect x="210" y="14" width="140" height="28"/>'+
  '<rect x="322" y="28" width="126" height="28"/>'+
  '<rect x="420" y="42" width="112" height="28"/>'+
  '<rect x="252" y="42" width="28" height="56"/>'+
  '<rect x="462" y="70" width="28" height="42"/>'+
  '</g>'+
  '<g fill="#63472c">'+
  '<rect x="84" y="14" width="126" height="14"/>'+
  '<rect x="210" y="28" width="112" height="14"/>'+
  '<rect x="322" y="42" width="98" height="14"/>'+
  '<rect x="420" y="56" width="112" height="14"/>'+
  '<rect x="266" y="70" width="14" height="28"/>'+
  '<rect x="476" y="98" width="14" height="14"/>'+
  '</g>'+
  pxFlower(126,49,"#fba9cd","#f78fbd")+
  pxFlower(196,70,"#f78fbd","#e0679d")+
  pxFlower(322,77,"#fba9cd","#f78fbd")+
  pxFlower(266,119,"#f78fbd","#e0679d")+
  pxFlower(420,91,"#fba9cd","#f78fbd")+
  pxFlower(476,133,"#f78fbd","#e0679d")+
  pxFlower(546,56,"#fba9cd","#f78fbd")+
  '<g fill="#f7aecd">'+
  '<rect x="168" y="28" width="14" height="14"/>'+
  '<rect x="378" y="56" width="14" height="14"/>'+
  '<rect x="518" y="28" width="14" height="14"/>'+
  '<rect x="308" y="154" width="14" height="14"/>'+
  '</g>'+
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
