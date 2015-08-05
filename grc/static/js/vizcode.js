var width = 1000
var height = 1000
// JS style enums - https://stijndewitt.wordpress.com/2014/01/26/enums-in-javascript/
var vizTypes = {
  AUTHOR_COLLAB: 1,
  SIMILARITY: 2,
  // etc.
}
// Start with author collaboration graph as default on page load
var currentViz = vizTypes.AUTHOR_COLLAB

var colors = d3.scale.category10();
var linkColour = "#bbb"

var svg = d3.select("#svgDiv")
    .append("svg")
    .attr("id", "svgArea");

// svg elements to hold links and nodes respectively
// the link group is appended first so that the visual circle elements will cover the line elements
// that way the edges connect to the outside of the nodes rather than the centre
var linkGroup = svg.append("g").attr("id", "link_display");
var nodeGroup = svg.append("g").attr("id", "node_display");

var force = d3.layout.force()
    .gravity(0.10)
    //.distance(200) TODO what is this?
    .linkDistance([100])
    .charge(-220)
    .size([width, height]);

// OPTIONS
var just_school = true;
var frozen = false;
var labeled = true;

var nodeSelected = false;
var clickedNodeId;

var nodeScale = d3.scale.log()
.domain([1, 250])
.range([5, 30])
.base([10]);

var linkScale = d3.scale.log()
.domain([1, 100])
.range([1, 8])
.base([10]);


// TODO change back
var defaultGraph = "cswithattribs2"
//var defaultSchool = "cssimgraph"
//var thing;

// get_json is the url which maps to the django view which loads the json file and returns the data
d3.json('get_json/', function(error, data) {
  //for some reason d3.json() is not parsing the data, have to parse it
  var thing = JSON.parse(data)
  //console.log(thing.links);
  //console.log("bla blue blee")
  startItUp(thing)
});


//startItUp(thing);

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
      console.log("HAHAHUOU")
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
      console.log(links)

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

      d3.select("#edgeCount").text("Number of links: " + link[0].length);

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
                return "green";
              else
                return "blue";
          })
          .style("stroke", "black");

          if(labeled)
            addLabels(nodeG);

          nodeG.append("title")
          .text(function(d) {
            return d.name
          });

      
        // Remove the elements that no longer have data attached - i.e. the nodes that aren't in filtered nodes
        //TODO this is no longer needed - removing above
        //  node.exit().remove();

          // attach event listeners here so they get attached to new nodes as well
          node.on("mouseover", highlight);
          node.on("mouseout", lowlight);
          node.on("dblclick", highlight);
          node.on("dblclick", fixNode)
          node.on("click", showCollabInfo);

          d3.select("#nodeCount").text("Number of Nodes: " + node[0].length);
    }



    var addLabels = function(sel) {
      sel.append("text")
        .attr("font-size", "10px")
        .attr("font-family", "sans-serif")
        .text(function(d) { 
          return d.name })
        .attr("dy", ".35em")
        .attr("text-anchor", "middle")
        .attr("font-weight", "bold");
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
            return 0.1
        });

        node.style("opacity", function(o) {
          if (neighbours(d, o))
            return 1.0
          else
            return 0.1
        });
        d3.select(this).style("opacity", 1.0);
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
      var info = d.id + "</br></br>Collaborators:</br>"
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
          info += con.target.id + " (<span class=\"numCollabs\" id=\"" + 
            con.source.id + "-" + con.target.id + "\">" + con.num_collabs + "</span>)</br>"
        else
          info += con.source.id + " (<span class=\"numCollabs\" id=\"" + 
            con.source.id + "-" + con.target.id + "\">" + con.num_collabs + "</span>)</br>"
      }

      d3.select("#infoArea").html(info);
      d3.selectAll(".numCollabs").on("click", showTitles)              
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
      //TODO set charge depending on size of node
      /*force.charge(function(d, i) {
        if(nodeScale(d.paper_count) >= 15)
          return -200;
        else
          return -100;
      });*/
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
        startForce(allNodes, allLinks);
        updateLinks(allLinks);
        updateNodes(allNodes);
        //force.start();

        just_school = false;
      }
      else {
        startForce(filteredNodes, filteredLinks);
        updateLinks(filteredLinks);
        updateNodes(filteredNodes);
        //force.start();

        just_school = true;
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

    d3.select('#labels').on("click", function() {
      if(labeled) {
        svg.selectAll("text").remove();
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
        bffText += "</br>" + bffs[i].source.id + ", " + bffs[i].target.id + " (" + bffs[i].num_collabs + ")</br>"
      }
      d3.select("#infoArea").html(bffText);
    });

    d3.select('#searchBox').on("keyup", function() {
      searchText = this.value.toLowerCase();
      d3.selectAll(".nodeCircle").style("stroke", function(d) {
        if(d.id.toLowerCase().indexOf(searchText) != -1 && searchText.length > 0)
          return "orange"; })
        .style("stroke-width", function(d) {
          if(d.id.toLowerCase().indexOf(searchText) != -1 && searchText.length > 0)
            return "3px";
        });           
    });
  
    function showTitles() {
      var elemId = this.id;
      // Need to get the link which corresponds to this number of papers...
      // there must be a nicer way of doing this?
      link.each(function(l) {
        if(l.source.id + "-" + l.target.id === elemId) {
          
          var titles = l.collab_titles;
          
          var titleString = "<strong>Papers connecting " + l.source.id + " and " + l.target.id + "</strong><br><br>";
          
          for(var i = 0; i < titles.length; i++)
            titleString += titles[i] + "<br><br>"
          
          d3.select("#infoArea").html(titleString);
        }
      });
    }



  //});
}

d3.select("#schoolChooser").on("change", function() {
  var choice = this.value;
  startItUp(choice);
});
