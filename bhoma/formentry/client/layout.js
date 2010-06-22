
function removeAllChildren (element) {
  while (element.hasChildNodes()) {
    element.removeChild(element.firstChild);
  }
}

function render_viewport (vp, scene_graph) {
  var viewport = document.getElementById(vp);
  removeAllChildren(viewport);
  scene_graph.render(viewport);
}

function Indirect () {
  this.content = null;
  
  this.render = function (parent) {
    this.content.render(parent);
  }
}

function Layout (id, num_rows, num_cols, widths, heights, margins, spacings, color, margin_color, spacing_color, content) {
  this.id = id;

  this.num_rows = num_rows;
  this.num_cols = num_cols;
  if (num_rows < 1 || num_cols < 1) {
    throw new Error("invalid dimensions");
  }
  
  if (widths instanceof Array) {
    if (widths.length != num_cols) {
      throw new Error("widths don't match # cols");
    }
    this.widths = widths;
  } else { //single width to use for all columns
    this.widths = [];
    for (i = 0; i < num_cols; i++) {
      this.widths.push(widths)
    }
  }

  if (heights instanceof Array) {
    if (heights.length != num_rows) {
      throw new Error("heights don't match # rows");
    }
    this.heights = heights;
  } else { //single width to use for all columns
    this.heights = [];
    for (i = 0; i < num_rows; i++) {
      this.heights.push(heights)
    }
  }

  if (margins instanceof Array) {
    this.l_margin = margins[0];
    this.r_margin = margins[1];
    this.t_margin = margins[2];
    this.b_margin = margins[3];  
  } else {
    this.l_margin = margins;
    this.r_margin = margins;
    this.t_margin = margins;
    this.b_margin = margins;
  }
  
  if (spacings instanceof Array) {
    this.h_spacing = spacings[0];
    this.v_spacing = spacings[1];
  } else {
    this.h_spacing = spacings;
    this.v_spacing = spacings;
  }
  
  this.color = color;
  this.margin_color = margin_color;
  this.spacing_color = spacing_color;
  this.content = content;

  this.render = function (parent) {
    render_layout(this, parent);
  }
}

//todo: auto-sizing?
function TextButton (id, color, text_color, selected_color, inactive_color, caption, size_rel, onclick) {
  this.id = id;
  this.color = color;
  this.text_color = text_color;
  this.selected_color = selected_color;
  this.inactive_color = inactive_color;
  this.caption = caption;
  this.size_rel = size_rel;
  this.onclick = onclick;
  
  this.render = function (parent_div) {
    parent_div.id = uid(this.id);
    set_color(parent_div, this.color, parent_div.style.backgroundColor);
    parent_div.innerHTML = '<table border="0" cellpadding="0" cellspacing="0" width="100%" height="100%"><tr><td align="center" valign="center"><span></span></td></tr></table>'
    span = parent_div.getElementsByTagName('span')[0];
    span.style.fontWeight = 'bold';
    span.style.fontSize = this.size_rel * 100. + '%';
    span.style.color = this.text_color;
    span.textContent = this.caption;
    parent_div.onclick = this.onclick;
  }
}

//todo: auto-sizing?
function TextCaption (id, color, caption, size_rel, align, valign) {
  this.id = id;
  this.color = color;
  this.caption = caption;
  this.size_rel = size_rel;
  this.align = align;
  this.valign = valign;
  
  this.render = function (parent_div) {
    parent_div.id = uid(this.id);
    parent_div.innerHTML = '<table border="0" cellpadding="0" cellspacing="0" width="100%" height="100%"><tr><td align="' + this.align + '" valign="' + this.valign + '"><span></span></td></tr></table>'
    span = parent_div.getElementsByTagName('span')[0];
    span.style.fontWeight = 'bold';
    span.style.fontSize = this.size_rel * 100. + '%';
    span.style.color = this.text_color;
    span.textContent = this.caption;
  }
}

function uid (id) {
  if (id == null || id == '')
    id = "id-" + Math.floor(Math.random() * 1000000000);
    return id;
}

function new_div (id, top, left, width, height) {
  var div = document.createElement("div");
  div.id = uid(id);
  div.style.position = 'absolute';
  div.style.top = top + "px";
  div.style.left = left + "px";
  div.style.width = width + "px";
  div.style.height = height + "px";
  return div;
}

function endswith (x, suffix) {
  var sx = String(x);
  return sx.substring(sx.length - suffix.length) == suffix;
}

function partition (dim, cells, margin_lo, margin_hi, spacing) {
  //create partitions
  var sizes = new Array();
  var count = 2*cells.length + 1;
  for (var i = 0; i < count; i++) {
    if (i == 0) {
      sizes[i] = margin_lo;
    } else if (i == count - 1) {
      sizes[i] = margin_hi;
    } else if (i % 2 == 0) {
      sizes[i] = spacing;
    } else {
      sizes[i] = cells[(i - 1) / 2];
    }
  }
  
  //normalize percentage-based widths
  var pct0 = 0.;
  var px0 = 0;
  for (var i = 0; i < sizes.length; i++) {
    if (endswith(sizes[i], '%')) {
      var pct = parseFloat(sizes[i].substring(0, sizes[i].length - 1)) / 100.;
      var px = Math.round(dim * (pct0 + pct)) - px0;
      sizes[i] = px;
      pct0 += pct;
      px0 += px;
    }
  }
  //pct0 and px0 needed to evenly distribute rounding error
  
  //normalize proportional-based widths
  var sum = 0;
  var proport = new Array();
  var sum_proport = 0.;
  for (var i = 0; i < sizes.length; i++) {
    if (endswith(sizes[i], '*')) {
      var sfactor = sizes[i].substring(0, sizes[i].length - 1);
      var prop = Math.round(sfactor.length > 0 ? parseFloat(sfactor) : 1.);
      proport.push(prop)
      sum_proport += prop;
    } else {
      sum += sizes[i];
      proport.push(-1);
    }
  }
  if (sum > dim) {
    throw Error("too big for allowed width!")
  }
  var pp0 = 0.;
  var px0 = 0;
  for (var i = 0; i < proport.length; i++) {
    if (proport[i] != -1) {
      var px = Math.round((dim - sum) * (pp0 + proport[i]) / sum_proport) - px0;
      sizes[i] = px;
      pp0 += proport[i];
      px0 += px;
    }
  }
  //pp0 and px0 needed to evenly distribute rounding error
  
  var sum = 0;
  for (var i = 0; i < sizes.length; i++) {
    sum += sizes[i];
  }
  if (sum != dim) {
    throw Error("not all space consumed!");
  }
  
  return sizes;
}

function offsets (dims) {
  var off = 0;
  var offs = new Array();
  for (var i = 0; i < dims.length; i++) {
    offs.push(off);
    off += dims[i];
  }
  return offs;
}

function set_color (elem, color, fallback_color) {
  elem.style.backgroundColor = (color != null && color != '' ? color : fallback_color);
}

function ainv (arr, i) {
  return arr[arr.length - Math.abs(i)];
}

function render_layout (layout, parent_div) {
  var widths = partition(parent_div.clientWidth, layout.widths, layout.l_margin, layout.r_margin, layout.h_spacing);
  var heights = partition(parent_div.clientHeight, layout.heights, layout.t_margin, layout.b_margin, layout.v_spacing);
  var woff = offsets(widths);
  var hoff = offsets(heights);
  var parent_color = parent_div.style.backgroundColor;
  
  if (has_margins(widths, heights)) {
    var inner_area = new_div(parent_div.id + '-inner', hoff[1], woff[1], ainv(woff, -1) - widths[0], ainv(hoff, -1) - heights[0]);
    parent_div.appendChild(inner_area);
    set_color(parent_div, layout.margin_color, parent_color);
  } else {
    var inner_area = parent_div;
  }
  
  if (has_spacing(widths, heights)) {
    set_color(inner_area, layout.spacing_color, parent_color);
  }
  
  for (var r = 0; r < layout.num_rows; r++) {
    for (var c = 0; c < layout.num_cols; c++) {
      var x = woff[2*c + 1];
      var y = hoff[2*r + 1];
      var w = widths[2*c + 1];
      var h = heights[2*r + 1];
      
      var subcontent = layout.content[layout.num_cols * r + c];
      var subcell = new_div(subcontent != null ? subcontent.id : parent_div.id + '-' + null + '-' + r + '-' + c, y, x, w, h);
      set_color(subcell, layout.color, parent_color);
      parent_div.appendChild(subcell);
      if (subcontent != null) {
        subcontent.render(subcell);
      }
    }
  }
}

function has_margins (widths, heights) {
  return widths[0] > 0 || ainv(widths, -1) > 0 || heights[0] > 0 || ainv(heights, -1) > 0;
}

function has_spacing (widths, heights) {
  return (widths.length > 3 || heights.length > 3) && (widths[2] > 0 || heights[2] > 0);
}


/*
layout
caption
button
textfield
*/