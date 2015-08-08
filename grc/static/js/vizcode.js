

var width = 1000
var height = 650
// JS style enums - https://stijndewitt.wordpress.com/2014/01/26/enums-in-javascript/
var vizTypes = {
  AUTHOR_COLLAB: 1,
  SIMILARITY: 2,
  // etc.
}
// Start with author collaboration graph as default on page load
var currentViz = vizTypes.AUTHOR_COLLAB

var multiColour = d3.scale.category10().domain([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
var moreColour = d3.scale.category20().domain(d3.range(0, 20))
var metricColour = d3.scale.linear();
var linkColour = "#bbb";
var inSchoolColour = Math.floor(Math.random() * 10)
var nonSchoolColour = Math.abs(inSchoolColour - 5)


var close = "<span class=\"clickable\" id=\"close\">close</span><br>";

var svg = d3.select("#svgDiv")
    .append("svg")
    .attr("height", height)
    //TODO make size responsive..
    .attr("width", "100%")
    .attr("id", "svgArea");
   // .style("border", "1px solid yellow");

var nameText = svg.append("text")
                  .attr("x", 0)
                  .attr("y", "10%")
                  .attr("class", "displayText")
                  .text("hello");

var typeText = svg.append("text")
                  .attr("x", 0)
                  .attr("y", "20%")
                  .attr("class", "displayText")
                  .text("world");

var nodeCountText = svg.append("text")
                  .attr("x", 0)
                  .attr("y", "30%")
                  .attr("class", "numText");
                 /* .text("node count goes here")*/

var edgeCountText = svg.append("text")
                   .attr("x", 0)
                  .attr("y", "35%")
                  .attr("class", "numText");
                /*  .text("edge count goes here")*/

var keyStartY = height/2.3

var keyGroup = svg.append("g")
                  .attr("class", "key");
                //.attr("x", 0)
                //.attr("y", "60%")
               /* .append("text")
                .attr("x", 0)
                .attr("y", "60%")
                .text("testing");*/



// svg elements to hold links and nodes respectively
// the link group is appended first so that the visual circle elements will cover the line elements
// that way the edges connect to the outside of the nodes rather than the centre
var linkGroup = svg.append("g").attr("id", "link_display");
var nodeGroup = svg.append("g").attr("id", "node_display");

var k = Math.sqrt(57 / (width * height));

var force = d3.layout.force()
    .gravity(100 * k)
    //.distance(200) TODO what is this?
    .linkDistance([100])
    .charge(-10/k)
    .size([width, height]);

// OPTIONS
//TODO n.b. just_school is always true by default so put inside functions
//var just_school = true;
var frozen = false;
var labeled = true;

var nodeSelected = false;
var clickedNodeId;

var nodeScale = d3.scale.log();
//.domain([1, 300])
/*.range([5, 30])
.base([10]);*/

var linkScale = d3.scale.log()
.domain([1, 100])
.range([1, 8])
.base([10]);


// TODO change back
var defaultGraph = "cswithattribs2"
//var defaultSchool = "cssimgraph"
//var thing;





function startItUp(graph) {
// TODO n.b. need to send data to server to get right json back; so not sure we can do everything directly inside
// d3.json, may have to get data first and then just pass it to another method; see above
// d3.json('get_json/', function(error, graph)  {
  
  // for d3 force layout to work, the links can reference the actual source and target node objects
  // or they can reference the index of the objects in the nodes array
  // networkx's json string uses the index referencing
  // however if we want to add or remove nodes from the array (to filter the data that we want to
  // see), the index referencing will not work, as nodes will not be in the positions referenced by the links
  // so here we replace the references to indices with the references to the objects themselves
  for(var i=0; i < graph.links.length; i++) {
    graph.links[i].source = graph.nodes[graph.links[i].source];
    graph.links[i].target = graph.nodes[graph.links[i].target];
  }


  var allLinks = graph.links
  var allNodes = graph.nodes
  var currentLinks = allLinks
  var currentNodes = allNodes
  console.log(allLinks)

    
  just_school = true;
  // If viewing an author collaboration graph (the default), allow for filtering between
  // school-only authors and full set (includes authors who collaborate with school-only)
  if(currentViz == vizTypes.AUTHOR_COLLAB) {
    // NB this is the JS array filter() not the d3 filter being used here
    // This gets just the links whose nodes both represent authors belonging to the school being displayed
    var filteredLinks = graph.links.filter(function(l) {
      return l.source.in_school && l.target.in_school;
    });
    // This gets just the nodes that represent authors belonging to the school being displayed
    var filteredNodes = graph.nodes.filter(function(n) {
      return n.in_school;
    });
    currentLinks = filteredLinks;
    currentNodes = filteredNodes;
  }

  // link will hold all the visual elements representing links
  var link
  // node will hold all the visual elements representing nodes
  var node

  // custom drag behaviour for use in frozen mode
  // doesn't use force.drag as that reactivates force automatically
  var staticDrag = d3.behavior.drag()
          .on("dragstart", dragstart)
          .on("drag", dragmove)
          .on("dragend", dragend);

  // Create a map indicating whether 2 nodes are adjacent, to make it faster to check this when necessary
  // idea from Mike Bostock - http://stackoverflow.com/a/8780277
  var neighboursMap = {}
  for(var i=0; i < allLinks.length; i++) {
    neighboursMap[allLinks[i].source.id + "," + allLinks[i].target.id] = 1;
    neighboursMap[allLinks[i].target.id + "," + allLinks[i].source.id] = 1;
  }

  // Add the node and link data to the layout and start the simulation
  // NB apparently should not be passing nodes and links again - just change variable?
  function startForce(nodes, links) {
    force.nodes(nodes)
          .links(links)
          .start();  
  }

  // Used to bind new link data to visual elements and display
  function updateLinks(links) {
    
    link = linkGroup.selectAll(".link")
          // Pass function as argument to data() to ensure that line elements are joined to the right link data
          // d.source.id - d.target.id uniquely identifies a link
          // See further explanation below when similar is done for the nodes
          .data(links, function(d) {
            return d.source.id + "-" + d.target.id;
          });

    console.log("in update links");
    console.log(link);
    console.log(link.enter())

    link.enter()
          .append("line")
          .attr("class", "link")
          .style("stroke", linkColour)
          .style("stroke-width", function(d) {
            if(d.num_collabs != undefined)
              return linkScale(d.num_collabs);
            else
              return 1;
          });

    link.exit().remove()
    console.log("getting here")

    //edgeCountText.text(link[0].length + " links");
   //link = svg.selectAll(".link")
  }

  // In static mode, disable highlighting when dragging a node
  function dragstart(d, i) {
    node.on("mouseover", null);
  }

  function dragmove(d, i) {
    // Change x and y coordinates of d to those of mouse, then call tick() to translate
    // tick() also moves links along with the node
    /*d.px += d3.event.dx;
    d.py += d3.event.dy;*/
    d.x = d3.event.x;
    d.y = d3.event.y;
    tick();
  }

    // reenable highlighting when finished dragging node
  function dragend(d, i) {
    node.on("mouseover", highlight)
  }

  // Used to bind new node data to visual elements and display
  function updateNodes(nodes) {
    // First remove nodes that are already present.
    // This is because a node may be present as a non-school member in one graph, but then
    // be a school member in the next. But would still be visualised as a non-school member as the visualisation
    // will not be refreshed for it (as it will be treated as an already existing element).
    // If we remove all existing elements first we ensure that every node gets visualised appropriately.
    // In practice this is almost equivalent to calling remove on data().exit() (i.e. the set of visual elements that
    // no longer have data attached to them) after renewing the data. But here we just remove before adding new data rather than
    // after.
    var existingNodes = nodeGroup.selectAll(".node");
    existingNodes.remove();

    node = nodeGroup.selectAll(".node")
        /* second argument to data() is a d3 "key function", used to join data to visual elements by the return value (a unique string,
         in this case the id)
         The default behaviour is joining by index - data is joined to elements in order. That wouldn't work here because we are using
         2 different sets of data (all the nodes and just the filtered nodes), so we need to associate elements to datums by their id.
         Example problem - we have an initial nodeset [a, b, c, d, e] they will be linked to node elements by index like so:
         a --> 0
         b --> 1
         c --> 2
         d --> 3
         e --> 4
         Then we filter the dataset to [b, d, e]
         b --> 0
         d --> 1
         e --> 2
         Because the new dataset is size 3, elements (0, 1, 2), previously linked to other data, remain, the others are discarded
         But the elements will still be displaying the names of nodes [a, b, c]
         If we associate data to elements by a key, then when [b, d, e] come in they will remain linked to their original elements:
         b --> 1
         d --> 3
         e --> 4  
        */
        .data(nodes, function(d) {
          return d.id;
        });

    // node.enter() returns data not attached to visual elements - since we removed all existing data above, all
    // data will be treated as new data 
    nodeG = node.enter()
        .append("g")
        .attr("class", "node")
        .call(force.drag);
        //.call(drag);

    var maxPapers = nodes[0].paper_count
    var minPapers = nodes[0].paper_count
    for(var i=1, len=nodes.length; i<len; i++) {
      if(nodes[i].paper_count < minPapers)
        minPapers = nodes[i].paper_count;
      else if(nodes[i].paper_count > maxPapers)
        maxPapers = nodes[i].paper_count;
    }

    maxSize = Math.min(40, 2300/nodes.length);
    minSize = maxSize/3
    nodeScale.domain([minPapers, maxPapers])
              .range([minSize, maxSize])
              .base([10]);  

    
    nodeG.append("circle")
      .attr("class", "nodeCircle")
      .attr("r", function(d) {
        if(d.paper_count != undefined)
          return nodeScale(d.paper_count);
        else
          return 10;
      })
      .style("fill", function(d, i) {
          //return colors(i);
          if(d.in_school)
            return multiColour(inSchoolColour);
          else
            return multiColour(nonSchoolColour);
      })
      .style("stroke", "black");

    if(labeled)
      addLabels(nodeG);

    nodeG.append("title")
    .text(function(d) {
      if(d.name)
        return d.name
      else
        return d.id
    });
      
    // Remove the elements that no longer have data attached - i.e. the nodes that aren't in filtered nodes
    //TODO this is no longer needed - removing above
    //  node.exit().remove();

      // attach event listeners here so they get attached to new nodes as well
      node.on("mouseover", highlight);
      node.on("mouseout", lowlight);
      //node.on("dblclick", highlight);
      //node.on("dblclick", fixNode)
      node.on("dblclick", showCollabInfo);

    // nodeCountText.text(node[0].length + " nodes");
  }


  var addLabels = function(sel) {
    sel.append("text")
      .attr("font-size", "10px")
      .attr("font-family", "sans-serif")
      .text(function(d) { 
        if(d.name)
          return d.name
        else
          return d.id
      })
      .attr("dy", ".35em")
      .attr("text-anchor", "middle")
      .attr("font-weight", "bold")
      .attr("class", "label");
  }

  function updateInfoText(links, nodes) {
    nodeCountText.text(nodes.length + " nodes");
    edgeCountText.text(links.length + " links");

    if(currentViz == vizTypes.AUTHOR_COLLAB && just_school == false) {
      a = [[multiColour(inSchoolColour), "school member"], [multiColour(nonSchoolColour), "non school member"]];
      makeKey(a);
    }

    if(currentViz == vizTypes.AUTHOR_COLLAB && just_school == true) {
      d3.selectAll(".keyCircle").remove();
      d3.selectAll(".keyText").remove();
    }
  }

  function makeKey(arr) {
    //First remove existing key
    d3.selectAll(".keyCircle").remove();
    d3.selectAll(".keyText").remove();

    for(var i=0; i<arr.length; i++) {
      var radius = 6;
      var yValue = keyStartY + (i * radius * 4)
      
      keyGroup.append("circle")
              .attr("class", "keyCircle")
              .attr("r", radius)
              .style("fill", arr[i][0])
              .style("stroke", "black")
              .attr("cx", radius + 10)
              .attr("cy", yValue);


      keyGroup.append("text")
              .attr("class", "keyText")
              .text(arr[i][1])
              .attr("x", radius*2 + 15)
              .attr("y", yValue + radius/2);
    }
  }

  highlight = function(d) {
   // alert(d.paper_count)
    if(!nodeSelected) {
      link.style("stroke", function(l) {
        if (l.source == d || l.target == d)
          return "red";
        else
          return "black";
      })
      .style("opacity", function(l) {
        if (l.source == d || l.target == d)
          return 1.0
        else
          return 0.2
      });

      node.style("opacity", function(o) {
        if (neighbours(d, o))
          return 1.0
        else if(d==o)
          return 1.0
        else
          return 0.2
      });
    }
  }

  var lowlight = function(d) {
    if(!nodeSelected) {
      link.style("stroke", linkColour)
      .style("opacity", 1.0);

      node.style("opacity", 1.0);
    }
  }

  var fixNode = function(d) {
    if(nodeSelected == true)
      nodeSelected = false;
    else
      nodeSelected = true;
  }

  var showCollabInfo = function(d) {
    var info = getAuthorNameHtml(d) + "<strong>" + d.name + "</strong></span></br></br>Collaborators:</br></br>"
    var connections = []
    link.each(function(l) {
      if(l.source == d || l.target == d) {
        connections.push(l)
      }
    });
        
    connections.sort(function(a, b) {
      return (b.num_collabs - a.num_collabs) 
    });
    
    
    for(var i=0; i<connections.length; i++) {
      var con = connections[i]
      if(d == con.source)
        info += getAuthorNameHtml(con.target) + con.target.name + "</span> (<span class=\"clickable numCollabs\" id=\"" + 
          con.source.id + "-" + con.target.id + "\">" + con.num_collabs + "</span>)</br></br>"
      else
        info += getAuthorNameHtml(con.source) + con.source.name + "</span> (<span class=\"clickable numCollabs\" id=\"" + 
          con.source.id + "-" + con.target.id + "\">" + con.num_collabs + "</span>)</br></br>"
    }

    displayInfoBox(info);
 

    d3.selectAll(".authorName").on("click", displayInfoForThisNode)
                                    .on("mouseover", highlightThisNode)
                                    .on("mouseout", lowlight);

    d3.selectAll(".numCollabs").on("click", showTitles);
  }

  function showTitles() {
    var elemId = this.id;
    // Need to get the link which corresponds to this number of papers...
    // there must be a nicer way of doing this?
    link.each(function(l) {
      console.log(l.source.id + "-" + l.target.id)
      if(l.source.id + "-" + l.target.id === elemId) {
        var title_urls = l.collab_title_urls;
        console.log(title_urls)
        
        var titleString = "<strong>Papers connecting " + getAuthorNameHtml(l.source) + l.source.name + 
        "</span> and " + getAuthorNameHtml(l.target) + l.target.name + "</span></strong><br><br>";
        console.log("BAAAFSDFSDAFSDAF");
        console.log(titleString);
        
        for(var i = 0; i < title_urls.length; i++)
          titleString += title_urls[i][0] + "<br><a href=\"" + title_urls[i][1] + "\" target=\"_blank\">link</a><br><br>"
        
        displayInfoBox(titleString);
        d3.selectAll(".authorName").on("click", displayInfoForThisNode)
                                    .on("mouseover", highlightThisNode)
                                    .on("mouseout", lowlight);
   
      }
    });
  }


  //helper function
  function getAuthorNameHtml(theNode) {
    return "<span class=\"clickable authorName\" id=\"" + theNode.id + "\">"
  }

  var displayInfoForThisNode = function() {
      var storedId = d3.select(this).attr("id");
      var theNode = getNodeFromId(storedId);
      showCollabInfo(theNode);
  }

  var highlightThisNode = function() {
    var storedId = d3.select(this).attr("id");
    var theNode = getNodeFromId(storedId);
    highlight(theNode)
  }

  function getNodeFromId(nodeId) {
    var theNodes = force.nodes();
    for(var i=0; i<theNodes.length; i++) {
      if(theNodes[i].id == nodeId)
        return theNodes[i];
    }
  }

  function displayInfoBox(text) {
    d3.select("#infoArea")
    .html(close + text)
    .style("visibility", "visible");

    d3.select("#close").on("click", function() {
      d3.select("#infoArea").style("visibility", "hidden");
    });

    $("#infoArea").draggable();   
  }


  function neighbours(n1, n2) {
    return neighboursMap[n1.id + "," + n2.id]
  }

  // Make graph static by stopping the force simulation
  // Attach drag event listener to nodes so they can be moved around in static mode
  function freeze() {
    force.stop();
    node.call(staticDrag);
  }

  // Restart simulation
  // Remove the static drag listener and reattach the normal force.drag listener
  function defrost() {
    node.on(".drag", null)
    node.call(force.drag);
    force.resume();
  }

  function update(links, nodes) {
    //TODO change back to filtered
    console.log("in update")
    console.log(links)
    updateLinks(links);
    updateNodes(nodes);
    updateInfoText(links, nodes);
    //TODO set charge depending on size of node

    // Formula to set appropriate gravity and charge as a function of the number of nodes
    // and the area
    // based on http://stackoverflow.com/a/9929599
    var k = Math.sqrt(nodes.length / (width * height));
    force.gravity(70 * k)
          .charge(-10/k)
          //.linkDistance([120])
          .linkDistance([0.8/k])

    startForce(nodes, links);
    // force simulation is running in background, position of things is changing with each tick
    // In order to see this visually, we need to get the current x and y positions on each tick and update the lines 
    force.on("tick", tick);
  }

  update(currentLinks, currentNodes)

  function tick() {
   link.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });
    // same with g elements, but these have no x and y, have to be translated
    node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
  }  


  d3.select("#filter").on("click", function() {                
    if(just_school) {
      
      just_school = false;
      update(allLinks, allNodes)
    }
    else {
      just_school = true;
      update(filteredLinks, filteredNodes)
      
    }
  });

  d3.select("#freeze").on("click", function() {
    if(frozen) {
      defrost();
      frozen = false;
    }
    else {
      freeze()
      frozen = true;
    }
  });

  d3.select('#togLabels').on("click", function() {
    if(labeled) {
      svg.selectAll(".label").remove();
      labeled = false;
    }
    else {
      addLabels(node);

      labeled = true;
    }
  });

  d3.select("#bff").on("click", function() {
    bffs = force.links()
    bffs.sort(function(a, b) {
      return b.num_collabs - a.num_collabs
    });

    var bffText = "Most Frequent Collaborators: </br>"
    // TODO 10 is a magic number
    for(var i = 0; i < 10; i++) {
      bffText += "</br>" + bffs[i].source.name + ", " + bffs[i].target.name + " (" + bffs[i].num_collabs + ")</br>"
    }

    displayInfoBox(bffText)
  });

  d3.select('#searchBox').on("keyup", function() {
    searchText = this.value.toLowerCase();
    d3.selectAll(".nodeCircle").style("stroke", function(d) {
      if(d.name.toLowerCase().indexOf(searchText) != -1 && searchText.length > 0)
        return "orange"; 
      else
        return "black";
      })
      .style("stroke-width", function(d) {
        if(d.name.toLowerCase().indexOf(searchText) != -1 && searchText.length > 0)
          return "3px";
      });           
  });




  d3.selectAll(".metricListItem").on("click", function() {
    listItem = d3.select(this);
    var metric = listItem.attr("id");
    var name = listItem.attr("data-name");
    var descrptn = listItem.attr("data-desc");
    colourByMetric(metric);
    var keyArray = [["white", "least " + name], ["red", "most " + name]];
    makeKey(keyArray);
    displayMetricText(metric, name, descrptn)
  });

  /*d3.select("#deg_cent").on("click", function() {
    colourByMetric("deg_cent");
    keyArray = [["white", "least degree centrality"], ["red", "most degree centrality"]];
    makeKey(keyArray);
    dscrptn = "a measure of etc. etc."
    displayMetricText("deg_cent", "degree centrality", dscrptn)
  });

  //TODO change key, text etc.

  d3.select("#bet_cent").on("click", function() {
    colourByMetric("between_cent");
    keyArray = [["white", "least betweenness centrality"], ["red", "most betweenness centrality"]];
    makeKey(keyArray);
    dscrptn = "a measure of influence bla bla"
    displayMetricText("between_cent", "betweenness centrality", dscrptn)
  });

  d3.select("#close_cent").on("click", function() {
    colourByMetric("close_cent");
    keyArray = [["white", "least closeness centrality"], ["red", "most closeness centrality"]];
    makeKey(keyArray);
    dscrptn = "yadda yadda yadda"
    displayMetricText("close_cent", "closeness centrality", dscrptn)
  });*/


  function colourByMetric(metric) {
    theNodes = force.nodes()
    max = Math.max.apply(Math,theNodes.map(function(n){
      return n[metric]
    }));
    min = Math.min.apply(Math,theNodes.map(function(n){
      return n[metric]
    }));
    metricColour.domain([min, max])
                .range(["white", "red"]);

    d3.selectAll(".nodeCircle").style("fill", function(d) {
      console.log("DEGEDSDAFDA")
      return metricColour(d[metric]);
    });
  }

  function displayMetricText(metric, name, description) {
    var infoText = description +
              "<br>Below is the " + name + " of the nodes in this graph, ranging from 0 to 1<br> \
              (note that this metric is calculated for the full graph, including non-school members)<br><br>"
    theNodes = force.nodes()  
    theNodes.sort(function(a, b) {
      return b[metric]-a[metric];
    });
    for(var i=0, len=theNodes.length; i<len; i++) {
      n = theNodes[i]
      infoText += n.name + ": " + Math.round(n[metric] * 1000) / 1000 + "<br>"
    }
    displayInfoBox(infoText)
  }

  d3.select("#community").on("click", function() {
    var circles = d3.selectAll(".nodeCircle").style("fill", function(d) {
      return moreColour(d.com);
    })
    var keyArray = []
    var commNums =[]
    theNodes = allNodes
    for(var i=0, len=theNodes.length; i<len; i++) {
      commNum = theNodes[i].com
      if(commNums.indexOf(commNum) < 0) {
        commNums.push(commNum);
        console.log("community number:")
        console.log(commNum);
        keyArray.push([moreColour(commNum), "a community"]);
      }
    }
    makeKey(keyArray);
  });


}


  //});
//}


// get_json is the url which maps to the django view which loads the json file and returns the data
/*d3.json('get_json/', function(error, data) {
  //for some reason d3.json() is not parsing the data, have to parse it
  var thing = JSON.parse(data)
  //console.log(thing.links);
  //console.log("bla blue blee")
  startItUp(thing)
});*/

/*d3.xhr('get_json/').header("Content-Type", "application/x-www-form-urlencoded").post("a=2", function(error, data) {
  console.log(data)
})*/

// Using jquery to make get request to server as was having trouble passing parameters in d3 requests
// get_json is the url which maps to the django view which loads the json file and returns the data
function getData(name, type) {
  console.log(name)
  $.get('get_json/', {name: name, type: type}, function(data) {
    graph_data = JSON.parse(data);
    startItUp(graph_data);
  });
}

$(function() {
  $('#dragtest').draggable({
    zIndex: 100
  });
});


d3.select("#schoolChooser").on("change", function() {
  var choice = this.value
  getData(choice, "collab");
});

d3.selectAll(".menuChoice").on("click", function() {
  var type = d3.select(this).attr("data-type");
  var name = d3.select(this).attr("data-name");
  var nmtext = d3.select(this).attr("data-nametext");
  var tptext = d3.select(this).attr("data-typetext");

  //display background text
  nameText.text(nmtext)
  typeText.text(tptext)
  //Get the new data
  getData(name, type);

  d3.select("#infoArea").style("visibility", "hidden");  
  inSchoolColour = Math.floor(Math.random() * 10)
  nonSchoolColour = Math.floor(Math.random() * 10)
  while(inSchoolColour == nonSchoolColour)
    nonSchoolColour = Math.floor(Math.random() * 10)
});

//getData("Dental School collab", "collab");
