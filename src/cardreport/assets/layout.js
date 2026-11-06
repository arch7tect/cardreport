(() => {
  const state = window.cardreport = {ready:false,error:null,pages:0};
  const settings = JSON.parse(document.getElementById('report-settings').textContent);
  const source = document.getElementById('source');
  const pages = document.getElementById('pages');
  const tolerance = 1; // CSS pixels, only for fractional layout rounding.
  const fail = (element, reason) => {const e=new Error((element.dataset.path || 'report') + ': ' + reason);e.name='LayoutOverflowError';throw e;};
  const rect = e => e.getBoundingClientRect();
  const visibleText = e => getComputedStyle(e).visibility !== 'hidden' && rect(e).width && rect(e).height;
  const labelName = e => `${e.closest('.xtick, .ytick')?.getAttribute('class') || (e.classList.contains('legendtext') ? 'legend' : 'value')} ${JSON.stringify(e.textContent)}`;
  function textCorners(element) {
    const b=element.getBBox(), m=element.getScreenCTM();
    if (!m) throw new Error('chart text has no screen transform');
    return [[b.x,b.y],[b.x+b.width,b.y],[b.x+b.width,b.y+b.height],[b.x,b.y+b.height]]
      .map(([x,y])=>({x:m.a*x+m.c*y+m.e,y:m.b*x+m.d*y+m.f}));
  }
  function overlaps(a,b) {
    // Axis-aligned boxes falsely intersect when Plotly rotates category labels.
    for (const polygon of [a,b]) for (let i=0;i<4;i++) {
      const p=polygon[i], q=polygon[(i+1)%4], length=Math.hypot(q.x-p.x,q.y-p.y);
      if (!length) continue;
      const x=-(q.y-p.y)/length, y=(q.x-p.x)/length;
      const pa=a.map(p=>p.x*x+p.y*y), pb=b.map(p=>p.x*x+p.y*y);
      if (Math.min(Math.max(...pa),Math.max(...pb))-Math.max(Math.min(...pa),Math.min(...pb))<=tolerance) return false;
    }
    return true;
  }
  async function reserveValueLabels(chart) {
    // Bounded layout passes; final bounds/plot-area checks still decide whether it fits.
    for (let pass=0;pass<2;pass++) {
      const cr=rect(chart), extra={l:0,r:0,t:0,b:0};
      for (const label of [...chart.querySelectorAll('.bartext-outside, .funneltext')].filter(visibleText)) {
        const r=rect(label);
        extra.l=Math.max(extra.l,cr.left-r.left);extra.r=Math.max(extra.r,r.right-cr.right);
        extra.t=Math.max(extra.t,cr.top-r.top);extra.b=Math.max(extra.b,r.bottom-cr.bottom);
      }
      const update={};
      // Plotly's computed margins include space added for axis labels.
      const size=chart._fullLayout?._size;
      for (const side of ['l','r','t','b']) if (extra[side]>tolerance) {
        if (!size || !Number.isFinite(size[side])) throw new Error('chart margin measurement unavailable');
        update['margin.'+side]=size[side]+Math.ceil(extra[side])+2;
      }
      if (!Object.keys(update).length) return;
      await Plotly.relayout(chart,update);
    }
  }
  let body;
  function newPage() {
    if (pages.children.length >= settings.pageLimit) fail(pages, 'page limit exceeded');
    const page=document.createElement('section');page.className='page';
    body=document.createElement('div');body.className='page-body';page.append(body);pages.append(page);
    return body;
  }
  function fits(e) {return rect(e).bottom<=rect(body).bottom+tolerance && rect(e).right<=rect(body).right+tolerance;}
  function pageEmpty() {return body.children.length===0;}
  function titleOnly() {return body.children.length===1 && body.firstElementChild.tagName==='HEADER';}
  function fragmentTable(block) {
    const table=block.matches('table') ? block : block.querySelector(':scope > .card-content > table');
    if (!table) return false;
    const rows=[...table.tBodies[0].rows];
    let fragment, target;
    function start() {
      fragment=block.cloneNode(true);
      target=fragment.matches('table') ? fragment : fragment.querySelector('table');
      target.tBodies[0].replaceChildren();body.append(fragment);
    }
    start();
    for (const row of rows) {
      target.tBodies[0].append(row);
      if (fits(fragment)) continue;
      row.remove();
      if (!target.tBodies[0].rows.length) fragment.remove();
      if (pageEmpty()) fail(block,'table row exceeds an empty page');
      if (titleOnly()) fail(block,'report title leaves no room for the first table row');
      newPage();start();target.tBodies[0].append(row);
      if (!fits(fragment)) fail(block,'table row exceeds an empty page');
    }
    return true;
  }
  async function run() {
    await Promise.all([document.fonts.load('12px CardReport'),document.fonts.load('bold 12px CardReport')]);
    if (!document.fonts.check('12px CardReport') || !document.fonts.check('bold 12px CardReport')) throw new Error('report: bundled font unavailable');
    const blocks=[...source.children];newPage();let pendingBreak=false;
    for (const block of blocks) {
      if (block.dataset.kind==='PageBreak') {pendingBreak=!!body.children.length && !titleOnly();continue;}
      if (pendingBreak) {newPage();pendingBreak=false;}
      if (settings.mode==='flow' && (block.matches('table') || block.matches('[data-kind=Card]') && block.querySelector(':scope > .card-content > table'))) {
        fragmentTable(block);continue;
      }
      body.append(block);
      if (settings.mode==='flow' && !fits(block)) {
        block.remove();if (pageEmpty()) fail(block,'block exceeds an empty page');
        if (titleOnly()) fail(block,'report title leaves no room for the first block');
        newPage();body.append(block);if (!fits(block)) fail(block,'block exceeds an empty page');
      }
    }
    source.remove();
    for (const el of pages.querySelectorAll('.chart')) {
      const spec=settings.charts[el.id];
      if (el.clientHeight < (spec.compact ? 10 : 35)*96/25.4-1 || el.clientWidth<40) fail(el,'chart has insufficient allocated space');
      await Plotly.newPlot(el,spec.data,{...spec.layout,width:el.clientWidth,height:el.clientHeight},
          {staticPlot:true,displayModeBar:false,responsive:false,typesetMath:false});
      await reserveValueLabels(el);
    }
    await document.fonts.ready;
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    for (const pb of pages.querySelectorAll('.page-body')) {
      if (pb.scrollHeight>pb.clientHeight+tolerance || pb.scrollWidth>pb.clientWidth+tolerance) fail(pb,'page content exceeds available space');
    }
    for (const el of pages.querySelectorAll('[data-path], .card-content')) {
      if (el.classList.contains('chart')) continue;
      if (el.scrollHeight>el.clientHeight+tolerance || el.scrollWidth>el.clientWidth+tolerance) fail(el,'content exceeds allocated width/height');
      // Min-size children can overflow grid tracks without increasing the parent's client size.
      const er=rect(el);
      for (const child of el.children) {
        const cr=rect(child);
        if (cr.width && cr.height && (cr.right>er.right+tolerance || cr.bottom>er.bottom+tolerance || cr.left<er.left-tolerance || cr.top<er.top-tolerance)) fail(el,'child exceeds allocated space');
      }
    }
    for (const frame of pages.querySelectorAll('.chart-frame')) {
      if (frame.querySelectorAll('.legend-item').length !== +frame.dataset.legendCount) fail(frame, 'category legend entries were omitted');
    }
    for (const chart of pages.querySelectorAll('.chart')) {
      const cr=rect(chart);
      const spec=settings.charts[chart.id];
      if (spec.categoryCount !== null && chart.querySelectorAll(spec.categoryAxis+'tick text').length!==spec.categoryCount) fail(chart,'category labels were omitted');
      const plot=chart.querySelector('clipPath.plotclip rect');
      if (plot && (+plot.getAttribute('width')<40 || +plot.getAttribute('height')<(spec.compact ? 20 : 40))) fail(chart,'labels leave insufficient plotting area');
      const texts=[...chart.querySelectorAll('svg text')].filter(visibleText);
      for (const t of texts) {
        const tr=rect(t);
        if (tr.left<cr.left-tolerance || tr.right>cr.right+tolerance || tr.top<cr.top-tolerance || tr.bottom>cr.bottom+tolerance) fail(chart,'chart label exceeds available space: '+labelName(t));
      }
      for (const selector of ['.xtick text, .ytick text, .legendtext, .bartext, .funneltext']) {
        const labels=[...chart.querySelectorAll(selector)].filter(visibleText);
        const rs=labels.map(textCorners);
        for(let i=0;i<rs.length;i++) for(let j=i+1;j<rs.length;j++) {
          const a=rs[i], b=rs[j];
          if (overlaps(a,b)) fail(chart,'chart labels overlap: '+labelName(labels[i])+' and '+labelName(labels[j]));
        }
      }
    }
    state.pages=pages.children.length;state.ready=true;
  }
  run().catch(error=>{
    state.error={kind:error.name==='LayoutOverflowError'?'LayoutOverflowError':'RenderError',message:error.message};
    const el=document.getElementById('report-error');el.hidden=false;el.textContent='Report cannot be rendered: '+error.message;
  });
})();
