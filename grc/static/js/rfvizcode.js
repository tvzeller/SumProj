
(function() {

  // To be used as the width and height of the SVG visualisation area
  var width = 1000
  var height = 650

  // JS style enums - https://stijndewitt.wordpress.com/2014/01/26/enums-in-javascript/
  var vizTypes = {
    AUTHOR_COLLAB: 1,
    SIMILARITY: 2,
    SHORTEST: 3,
    SINGLE: 4,
    INTER: 5,
    TERMSEARCH: 6,
    COMMUNITIES: 7,
    // etc.
  }  

  // Start with author collaboration graph as default on page load
  var currentViz = vizTypes.AUTHOR_COLLAB
  var metricView = false;
  // When metricView is true
  var lastInfoBox;

  // To be used to stop simulation after a certain amount of time
  var freezeTimeOut;

  // OPTIONS
  // Variables to keep track of whether the visualisation is static or not, and whether nodes are labelled
  var frozen = false;
  var labeled = false;


  // Used to avoid dragging being treated like a click
  var downX;
  var downY;

  // Array to keep track of which nodes have been searched for in the graph - to keep them highlighted
  var searchedNodes = []

  var SHORTESTPATHERROR = 1;
  var LONGESTPATHERROR = 2;

  // HTML to be used to be added to text area to enable hiding it
  var close = "<span class=\"clickable\" id=\"close\">close</span><br>";
  // metrics options are removed from certain views - this holds the html to reactivate them when necessary
  var metricsHtml = d3.select("#metricsList").html();
  
  //Add svg area and default visual elements
  var svg = d3.select("#svgDiv")
      .append("svg")
      .attr("height", height)
      .attr("width", "100%")
      .attr("id", "svgArea");

  var nameText = svg.append("text")
                    .attr("x", 0)
                    .attr("y", "8%")
                    .attr("class", "displayText")

  var typeText = svg.append("text")
                    .attr("x", 0)
                    .attr("y", "12%")
                    .attr("class", "displayText")

  var nodeCountText = svg.append("text")
                    .attr("x", 0)
                    .attr("y", "18%")
                    .attr("class", "numText");               

  var edgeCountText = svg.append("text")
                     .attr("x", 0)
                    .attr("y", "21%")
                    .attr("class", "numText");

  var keyStartY = height/2.7

  var keyGroup = svg.append("g")
                    .attr("class", "key");



  // svg elements to hold links and nodes respectively
  // the link group is appended first so that the visual circle elements will cover the line elements
  // that way the edges connect to the outside of the nodes rather than the centre
  var linkGroup = svg.append("g").attr("id", "link_display");
  var nodeGroup = svg.append("g").attr("id", "node_display");


  // Declare d3 force layout variable
  var force = d3.layout.force()
      .size([width, height]);



  //D3 colour scales
  var multiColour = d3.scale.category10().domain([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
  var moreColour = d3.scale.category20().domain(d3.range(0, 20))
  var metricColour = d3.scale.linear();
  var linkColour = "#bbb";
  // Colours to use on default graph
  var inSchoolColour = Math.floor(Math.random() * 10)
  var nonSchoolColour = Math.abs(inSchoolColour - 5)
 
  //D3 scales to use to determine node radius and link width
  var nodeScale = d3.scale.log();
  var linkScale = d3.scale.log();


  // Function that gets called every time new data (a new graph) is obtained from the server
  function startItUp(graph) {

    /* 
    For d3 force layout to work, the links can reference the actual source and target node objects
    or they can reference the index of the objects in the nodes array.
    Networkx's json string uses index referencing.
    However if we want to add or remove nodes from the array (to filter the data that we want to
    see), the index referencing will not work, as nodes will not be in the positions (indices) referenced by the links
    so here we replace the references to indices with the references to the objects themselves
    */
    for(var i=0; i < graph.links.length; i++) {
      graph.links[i].source = graph.nodes[graph.links[i].source];
      graph.links[i].target = graph.nodes[graph.links[i].target];
    }

    // Variables to hold all of the nodes and links in this data. This will allow returning from a filtered view of the graph
    var allLinks = graph.links;
    var allNodes = graph.nodes;
    // Variables to hold the links and nodes currently displayed
    var currentLinks = allLinks;
    var currentNodes = allNodes;
    // When filtering links by year, need a way to go back to all the links (for all time) - this holds those links
    // Set to allLinks at first
    var allTimeLinks = allLinks;

    /* Collaboration graphs can show either just members of the current school or also people outside 
    the school who they have collaborated with. just_school variable keeps track of which is currently the case.
    */
    var just_school = true;
    // If viewing an author collaboration graph or a keyword similarity graph, allow for filtering between
    // school-only authors and full set by keeping the filtered set of nodes and links in variables
    if(currentViz == vizTypes.AUTHOR_COLLAB || currentViz == vizTypes.SIMILARITY) {
      // Filter to get just the links whose nodes both represent authors belonging to the school being displayed
      var filteredLinks = graph.links.filter(function(l) {
        return l.source.in_school && l.target.in_school;
      });
      // Filter to get just the nodes that represent authors belonging to the school being displayed
      var filteredNodes = graph.nodes.filter(function(n) {
        return n.in_school;
      });
      // Set current links and nodes to the filtered down versions
      currentLinks = filteredLinks;
      currentNodes = filteredNodes;
      allTimeLinks = filteredLinks;
    }

    // link will hold all the visual elements representing links
    var link
    // node will hold all the visual elements representing nodes
    var node

    // Custom drag behaviour for use in frozen mode
    // Doesn't use the D3 default force.drag as that reactivates the force automatically
    var staticDrag = d3.behavior.drag()
           // .on("dragstart", dragstart)
            .on("drag", dragmove);

    // dragmove() enables dragging a node when in static mode.
    function dragmove(d, i) {
      // Change x and y coordinates of d to those of mouse, then call tick() to actually move the visual elements
      // tick() also moves links along with the node
      d.x = d3.event.x;
      d.y = d3.event.y;
      tick();
      console.log("DRAGGGGIN");
    }


    // Create a map indicating whether 2 nodes are adjacent, to make it faster to check this when necessary
    // This is used when highlighting paths and neigbours
    // idea from Mike Bostock - http://stackoverflow.com/a/8780277
    var neighboursMap = {}
    for(var i=0; i < allLinks.length; i++) {
      neighboursMap[allLinks[i].source.id + "," + allLinks[i].target.id] = 1;
      neighboursMap[allLinks[i].target.id + "," + allLinks[i].source.id] = 1;
    }


    // Used to bind new link data to visual elements and display
    function updateLinks(links) {
      
      // Get currently existing links and remove them; the same link may have different properties in different graphs
      var existingLinks = linkGroup.selectAll(".link");
      existingLinks.remove();

      // Here we assign the link data to visual elements using data()
      link = linkGroup.selectAll(".link")
            // Pass function as argument to data() to ensure that line elements are joined to the right link data
            // d.source.id - d.target.id uniquely identifies a link
            // See further explanation below when similar is done for the nodes
            .data(links, function(d) {
              return d.source.id + "-" + d.target.id;
            });

      if(links.length > 0 && links[0].num_collabs != undefined) {
        // Get the maximum number of collaborations
        maxCollabs = Math.max.apply(Math, links.map(function(l){
          return l.num_collabs;
        }));
        // Get the minimum number of collaborations
        minCollabs = Math.min.apply(Math, links.map(function(l){
          return l.num_collabs;
        }));

        // Set the scale for the link width
        linkScale.domain([minCollabs, maxCollabs])
                  .range([1, 8])
                  .base([10]);
      }  

      // link.enter() returns the links that are new to the visualisation; here we define the visual elements
      // that will be attached to the that data
      link.enter()
            .append("line")
            .attr("class", "link")
            .style("stroke", function(d) {
              return getLinkColour(d);
            })
            .style("stroke-width", function(d) {
              if(d.num_collabs != undefined) {
                  return linkScale(d.num_collabs);
              }
              // For cases where the link objects do not have a num_collabs property
              else
                return 1;
            });

      // link.exit() returns the visual elements that no longer have data attached; these are removed
      link.exit().remove()
    }

    // Function to determine what colour the link should be
    function getLinkColour(theLink) {
      if(currentViz == vizTypes.SIMILARITY) {
        // In a similarity graph, if nodes aren't actual coauthors, link between them is given a different colour
        if(!theLink.areCoauthors)
          return "#2ca02c";
        else
          return linkColour;
      }
      else
        return linkColour;
    }

    // Used to bind new node data to visual elements and display
    function updateNodes(nodes) {
      // First remove nodes that are already present.
      // This is because a node may be present as a non-school member in one graph, but then
      // be a school member in the next. But would still be visualised as a non-school member as the visualisation
      // will not be refreshed for it (as it will be treated as an already existing element).
      // If we remove all existing elements first we ensure that every node gets visualised appropriately.
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
          // force.drag lets us drag nodes when the simulation is
          .call(force.drag);

      if(nodes[0].paper_count != undefined) {
        // Get the maximum paper count in this graph
        var maxPapers = Math.max.apply(Math, nodes.map(function(n){
          return n.paper_count;
        }));
        // Get the minimum paper count in this graph
        var minPapers = Math.min.apply(Math, nodes.map(function(n){
          return n.paper_count;
        }));

        // Define max size of node radius
        // Dependent on amount of nodes, but with lower and upper bounds
        maxSize = Math.max(Math.min(40, 1200/nodes.length), 8);
        // Minimum node size is in proportion to maximum node size
        minSize = maxSize/2
        // Node size is a function of the amount of papers node has, within the bounds set above
        nodeScale.domain([minPapers, maxPapers])
                  .range([minSize, maxSize])
                  .base([10]);
      }  
      
      // Attach visual elements to new node data elements
      nodeG.append("circle")
        .attr("class", "nodeCircle")
        .attr("r", function(d) {
          // Radius of circles is determined by the type of visualisation currently active
          if(currentViz == vizTypes.AUTHOR_COLLAB || currentViz == vizTypes.SIMILARITY && d.paper_count != undefined)
            return nodeScale(d.paper_count);

          else if(currentViz == vizTypes.SHORTEST)
            return 20;

          else if(currentViz == vizTypes.SINGLE) {
            if(d.centre) {
              return Math.max(Math.min((width / nodes.length), 40), 8);
            }
            else
              return Math.max(Math.min((width / 2 / nodes.length), 20), 4);
          }

          else if(currentViz == vizTypes.TERMSEARCH) {
            if(d.isTerm)
              return 30;
            else
              return 15;
          }

          else
            return 10;
        })
        .style("stroke", "black"),

        // Call method to colour the nodes
        colourByDefault();

      // Add labels by default to search and shortest path visualisations
      if(currentViz == vizTypes.TERMSEARCH || currentViz == vizTypes.SHORTEST)
        addLabels(nodeG, "nameLabels");

      // Add tooltips to display names on hovering
      nodeG.append("title")
      .text(function(d) {
        if(d.name)
          return d.name
        else
          return d.id
      });

      // Clear searched nodes so that stroke width does not remain wider after graph is updated
      searchedNodes = []
        

      // Attach event handlers to node circles

      // Record mousedown coordinates to compare with mouseup coordinates
      // So that dragging a node does not do the same as just clicking it in place
      node.on("mousedown", function() {
        var coords = d3.mouse(this);
        downX = coords[0];
        downY = coords[1];
       });

      // On mouseup, check if the mouse coordinates have changed - if not, treat as click
      node.on("mouseup", function(d) {
        var coords = d3.mouse(this);
        var upX = coords[0];
        var upY = coords[1];
        if(upX == downX && upY == downY) {
          showCollabInfo(d)
          highlight(d);
        }
      });

      // Highlight node on hover
      d3.selectAll(".nodeCircle").on("mouseover", highlightJustNode);
      d3.selectAll(".nodeCircle").on("mouseout", lowlightJustNode);
    }

    //Function to add name labels to nodes
    var addLabels = function(sel, label) {
      sel.append("text")
        .attr("font-size", "10px")
        .attr("font-family", "sans-serif")
        .text(function(d) { 
          // TODO magic numbers...
          if(label=="nameLabels") {
            if(d.name)
              return d.name
            else
              return d.id
          }
          else if(label=="idLabels") {
            return d.id;
          }
        })
        .attr("dy", ".35em")
        .attr("text-anchor", "middle")
        .attr("font-weight", "bold")
        .attr("class", "label");
    }

    // Updates the text displaying number of nodes and links in a graph
    function updateInfoText(links, nodes) {
      nodeCountText.text(nodes.length + " nodes");
      edgeCountText.text(links.length + " links");
    }

    // Updates the colour key
    // Creates array of [colour, label] pairs to be passed to the function that draws the key
    function updateKey() {

      if((currentViz == vizTypes.AUTHOR_COLLAB || currentViz == vizTypes.SIMILARITY) && just_school == false) {
        var a = [[multiColour(inSchoolColour), "school member"], [multiColour(nonSchoolColour), "non school member"]];
      }

      // If just school members are displayed, no need for a key
      else if((currentViz == vizTypes.AUTHOR_COLLAB || currentViz == vizTypes.SIMILARITY) && just_school == true) {
        d3.selectAll(".keyCircle").remove();
        d3.selectAll(".keyText").remove();
        var a = [];
      }

      else if(currentViz == vizTypes.SHORTEST) {
        var a = [["#1f77b4", "source"], ["#d62728", "target"]];
      }

      else if(currentViz == vizTypes.SINGLE) {
        // Get the name central node (the author whose graph it is)
        var name = "";
        for(var i=0; i<currentNodes.length; i++) {
          if(currentNodes[i].centre)
            name = currentNodes[i].name;
        }
        var a = [[multiColour(0), name],];

        // Rest of nodes are coloured according to distance from central node, so make
        // key accordingly
        numHops = $("#cutoffInput").val()
        for(var i=1; i<=numHops; i++) {
          if(i==1)
            var hopString = " hop away";
          else
            var hopString = " hops away"
          a.push([multiColour(i), i + hopString]);
        }
      }

      else if(currentViz == vizTypes.INTER) {
        var a = []
        for(var i=0; i<currentNodes.length; i++)
          a.push([moreColour(currentNodes[i].name), currentNodes[i].name]);
      }
      // Finally call makeKey, passing it the array
      makeKey(a)
    }

    // Function to draw the colour key
    function makeKey(arr) {
      //First remove existing key
      d3.selectAll(".keyCircle").remove();
      d3.selectAll(".keyText").remove();
      // Adjust size of the key based on number of elements
      if(arr.length > 15) {
        var radius = 4.5;
        var textSize = 12;
      }
      else {
        var radius = 6;
        var textSize = 15;
      }

      for(var i=0; i<arr.length; i++) {
        var yValue = keyStartY + (i * radius * 4)
        
        keyGroup.append("circle")
                .attr("class", "keyCircle")
                .attr("r", radius)
                // Get the colour from the array argument
                .style("fill", arr[i][0])
                .style("stroke", "black")
                .attr("cx", radius + 1)
                .attr("cy", yValue);


        keyGroup.append("text")
                .attr("class", "keyText")
                // Get the text corresponding to the colour from the array
                .text(arr[i][1])
                .attr("x", radius*2 + 10)
                .attr("y", yValue + radius/2)
                .attr("font-size", 15);
      }
    }

    highlightJustNode = function(d) {
      //d3.select(this).style("stroke-width", "3px");
      //console.log(d3.select(this))
      //console.log(d);
      d3.selectAll(".nodeCircle").style("stroke-width", function(circ) {
        if(d == circ || searchedNodes.indexOf(circ) != -1)
          return "3px";
      })
    }

    function highlightNodeGroup(arr) {
      d3.selectAll(".nodeCircle").style("stroke-width", function(circ) {
        for(var i=0; i<arr.length; i++) {
          theNode = arr[i];
          if(circ==theNode)
            return "3px";
        }
      });
    }

    lowlightJustNode = function(d) {
      d3.selectAll(".nodeCircle").style("stroke-width", function(circ) {
        if(searchedNodes.indexOf(circ) != -1)
          return "3px";
      });
    }


    highlight = function(d) {
     // alert(d.paper_count)
      //if(true) {
      //alert("clicked");
      d3.selectAll(".singleLabel").remove()
      link.style("stroke", function(l) {
        if (l.source == d || l.target == d) {
          if(currentViz == vizTypes.SIMILARITY && !l.areCoauthors)
            return "#2ca02c";
          else
            return "#FF3030";
        }
        else
          //return linkColour;
          return getLinkColour(l);
      })
      .style("opacity", function(l) {
        if (l.source == d || l.target == d)
          return 1.0
        else
          return 0.15
      });

      node.style("opacity", function(o) {
        if (neighbours(d, o))
          return 1.0
        else if(d==o)
          return 1.0
        else
          return 0.15
      });

      if(!labeled) {
        d3.selectAll(".node").append("text")
                              .attr("class", "singleLabel")
                              .text(function(n) {
                              if(n==d)
                                return n.name;
                            })
                            .attr("font-size", "10px")
                            .attr("font-family", "sans-serif")
                            .attr("dy", ".35em")
                            .attr("text-anchor", "middle")
                            .attr("font-weight", "bold");
      }

      //}*/
    }

    var lowlight = function(d) {
      link.style("stroke", function(l) {
        return getLinkColour(l);
      })
      .style("opacity", 1.0);

      node.style("opacity", 1.0);
     
      d3.selectAll(".singleLabel").remove()
    }


    d3.select("#svgArea").on("click", function() {
      var coords = d3.mouse(this);
      var xClick = coords[0];
      var yClick = coords[1];
      var circles = d3.selectAll(".nodeCircle");
      var onCircle = false;
      /*for(var i=0; i<circles[0].length; i++) {
        console.log(d3.select(circles[0][i]).attr("r"));
        //console.log(d3.select(circles[0][i]).attr("x"));
      }*/
      for(var i=0; i<node[0].length; i++) {
        var xNode = node[0][i].__data__.x
        var yNode = node[0][i].__data__.y
        //console.log(xNode);
        var radius = d3.select(node[0][i].firstElementChild).attr("r");
        //TODO credit this stackoverflow
        onCircle = Math.sqrt((xClick - xNode)*(xClick - xNode) + (yClick - yNode) * (yClick - yNode)) < radius
        if(onCircle)
          break;
      }
      if(!onCircle) {
        lowlight();
        if(metricView == true) {
          lastInfoBox();
        }
        else
          d3.select("#infoArea").style("visibility", "hidden");
      }
    });

    var showCollabInfo = function(d) {
      var info = getAuthorNameHtml(d) + "<strong>" + d.name + "</strong></span></br></br>"
      if(currentViz == vizTypes.SIMILARITY) {
        console.log("SIMSIMSIM");
        info += "Keywords:<br><br>";
        keyword_scores = d.keywords;
        just_keywords = ""
        for(var i=0; i<keyword_scores.length; i++)
          just_keywords += keyword_scores[i][0] + " "

        info += just_keywords + "<br><br>";
        info += "Researchers with keywords in common<br><br>"
      }
      else
        info += /*getAuthorNameHtml(d) + "<strong>" + d.name + "</strong></span></br></br>*/"Collaborators:</br></br>";

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
   

      d3.selectAll(".authorName").on("click", function() {
                                      //var sel = d3.select(this);
                                      //var theId = sel.attr("id");
                                      var theId = d3.select(this).attr("id");
                                      displayInfoForThisNode(theId);
                                      highlightPathsForThisNode(theId);
                                        })
                                      .on("mouseover", highlightThisNode)
                                      .on("mouseout", lowlightJustNode);

      if(currentViz == vizTypes.SIMILARITY)
        d3.selectAll(".numCollabs").on("click", showKeywords);
      else
        d3.selectAll(".numCollabs").on("click", showTitles);
    }

    //N.b. connections is an array of links incident to the node whose collaborations are showing TODO not using this anymore
    function showTitles() {
      var elemId = this.id;
      console.log("elemid")
      //console.log(elemId);
      //console.log("LINK")
      //console.log(link)
      //console.log("jetsons")
      //theLinks = force.links()
      // Need to get the link which corresponds to this number of papers...
      // there must be a nicer way of doing this?
      link.each(function(l) {
      //for(var i=0; i<theLinks.length; i++) {
        //break;
        //var l = theLinks[i];
        //console.log(l.source.id + "-" + l.target.id)
        if(l.source.id + "-" + l.target.id === elemId) {
          var title_urls = l.collab_title_url_years;

          var titleString = "Papers connecting <strong>" + getAuthorNameHtml(l.source) + l.source.name + 
          "</span></strong> and <strong>" + getAuthorNameHtml(l.target) + l.target.name + "</span></strong><br><br>";
          
          for(var i = 0; i < title_urls.length; i++)
            titleString += title_urls[i][0] + "<br>" + title_urls[i][2] + "<br><a href=\"" + title_urls[i][1] + "\" target=\"_blank\">link</a><br><br>"
          
          displayInfoBox(titleString);
          d3.selectAll(".authorName").on("click", function() {
                                      //var sel = d3.select(this);
                                      //var theId = sel.attr("id");
                                      var theId = d3.select(this).attr("id");
                                      displayInfoForThisNode(theId);
                                      highlightPathsForThisNode(theId);
                                        })
                                      .on("mouseover", highlightThisNode)
                                      .on("mouseout", lowlightJustNode);
     
        }
      });
    }

    // TODO refactor to use just one method for show titles and show keywords
    function showKeywords() {
      var elemId = this.id;
      // Need to get the link which corresponds to this number of papers...
      // there must be a nicer way of doing this?
      link.each(function(l) {
        console.log(l.source.id + "-" + l.target.id)
        if(l.source.id + "-" + l.target.id === elemId) {
          var keywords = l.sim_kw;

          var titleString = "<strong>Keywords connecting " + getAuthorNameHtml(l.source) + l.source.name + 
          "</span> and " + getAuthorNameHtml(l.target) + l.target.name + "</span></strong><br><br>";
          
          for(var i = 0; i < keywords.length; i++)
            titleString += keywords[i] + "<br><br>"
          
          displayInfoBox(titleString);
          d3.selectAll(".authorName").on("click", function() {
                                      //var sel = d3.select(this);
                                      //var theId = sel.attr("id");
                                      var theId = d3.select(this).attr("id");
                                      displayInfoForThisNode(theId);
                                      highlightPathsForThisNode(theId);
                                        })
                                      .on("mouseover", highlightThisNode)
                                      .on("mouseout", lowlightJustNode);
     
        }
      });
    }


    //helper function
    function getAuthorNameHtml(theNode) {
      return "<span class=\"clickable authorName\" id=\"" + theNode.id + "\">"
    }

    var displayInfoForThisNode = function(anId) {
        //var storedId = d3.select(sel).attr("id");
        //console.log("THEID IS")
        var storedId = anId;
        var theNode = getNodeFromId(storedId);
        showCollabInfo(theNode);
    }

    var highlightThisNode = function() {
      var storedId = d3.select(this).attr("id");
      var theNode = getNodeFromId(storedId);
      highlightJustNode(theNode)
    }

    var highlightPathsForThisNode = function(anId) {
      //var storedId = d3.select(this).attr("id");
      var theNode = getNodeFromId(anId);
      highlight(theNode)
    }

    function getNodeFromId(nodeId) {
      var theNodes = force.nodes();
      for(var i=0; i<theNodes.length; i++) {
        if(theNodes[i].id == nodeId)
          return theNodes[i];
      }
    }

    function neighbours(n1, n2) {
      return neighboursMap[n1.id + "," + n2.id]
    }

    // Make graph static by stopping the force simulation
    // Attach drag event listener to nodes so they can be moved around in static mode
    function freeze() {
      console.log("FROZEN")
      force.stop();
      frozen = true;
      node.call(staticDrag);
    }

    // Restart simulation
    // Remove the static drag listener and reattach the normal force.drag listener
    function defrost() {
      node.on(".drag", null)
      node.call(force.drag);
      force.resume();
      frozen = false;
    }

    function update(links, nodes) {
      // Every time the graph is updated, clear any currently running time out
      clearTimeout(freezeTimeOut)
      // This timeout function stops the simulation after a certain amount of time
      var timeToFreeze = Math.min(5000 + (nodes.length * links.length), 15000);
      freezeTimeOut = setTimeout(function() {
        freeze();
        console.log("STOPPED")
      }, timeToFreeze);

      //TODO change back to filtered
      console.log("in update")
      console.log(links)

      updateLinks(links);
      updateNodes(nodes);
      updateInfoText(links, nodes);
      //TODO set charge depending on size of node?

      // Formula to set appropriate gravity and charge as a function of the number of nodes
      // and the area
      // based on http://stackoverflow.com/a/9929599
      var k = Math.sqrt(nodes.length / (width * height));
      force.gravity(70 * k)
            //.charge((-10/k)
              //TODO still be be revised
              .charge(function(d) {
                if(currentViz == vizTypes.SINGLE) {
                  if(d.centre)
                    return -20/k
                  else
                    return -10/k
                }
                else {
                  if(nodeScale(d.paper_count) > 20)
                    return -12/k;
                  else
                    return -10/k;
                }
              })
            //.charge(-350)
            //.linkDistance([120])
            .linkDistance(function(d) {
              if(currentViz == vizTypes.SHORTEST)
                return 60;
              else if(currentViz == vizTypes.SINGLE) {
                if(d.centre)
                  return 5/5;
                else
                  return 0.5/k
              }

              else
                //return 3;
                return 0.8/k;
            });

      if(currentViz == vizTypes.SINGLE) {
        for(var i=0; i<nodes.length; i++) {
          if(nodes[i].centre) {
            nodes[i].fixed = true;
            nodes[i].x = width/2
            nodes[i].y = height/2
          }
        }
      }

      //startForce(nodes, links);
      force.nodes(nodes)
            .links(links)
            .start();  
      // force simulation is running in background, position of things is changing with each tick
      // In order to see this visually, we need to get the current x and y positions on each tick and update the lines 

      force.on("tick", tick);
     
     /* updateLinks(links);
      updateNodes(nodes);
      updateInfoText(links, nodes);*/
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
      metricView = false;                
      if(just_school) {
        just_school = false;
        update(allLinks, allNodes)
        allTimeLinks = allLinks;
      }
      else {
        just_school = true;
        update(filteredLinks, filteredNodes)
        allTimeLinks = filteredLinks;
      }
      d3.select("#infoArea").style("visibility", "hidden");
      d3.select("#metricsList").html(metricsHtml);
      addMetricHandlers();
      addComHandler();
    });

    d3.select("#freeze").on("click", function() {
      if(frozen) {
        defrost();
        //frozen = false;
      }
      else {
        freeze()
        //frozen = true;
      }
    });

  //TODO put somewhere else
    //if(currentViz == vizTypes.AUTHOR_COLLAB) {
    function updateYearChooser() {
      theLinks = allTimeLinks;
      console.log("YEARRRS")
      var maxYear = Math.max.apply(Math, theLinks.map(function(l){
        for(var i=0; i<l.collab_title_url_years.length; i++)
          return l.collab_title_url_years[i][2]
      }));

      var minYear = Math.min.apply(Math, theLinks.map(function(l){
        for(var i=0; i<l.collab_title_url_years.length; i++)
          return l.collab_title_url_years[i][2]
      }));

      console.log("MAXYEAR");
      console.log(maxYear)
      console.log(minYear)
      yearChooser = d3.select("#yearChooser");
      var options = "<option value=\"all\">all time</option>";
      for(var i=maxYear; i>=minYear; i--) {
        options += "<option value=\"" + i + "\">up to " + i + "</option>"
      }
      yearChooser.html(options)

    //}
    }

    // TODO put this somewhere else
    if(currentViz != vizTypes.SIMILARITY) {
      updateYearChooser();
      d3.select("#yearDiv").style("visibility", "visible");
    }
    else
      d3.select("#yearDiv").style("visibility", "hidden");


    d3.select("#yearChooser").on('change', function() {
      chosenYear = this.options[this.selectedIndex].value;
      var theNodes = force.nodes()
      if(chosenYear === "all") {
        /*if(just_school) 
          update(filteredLinks, filteredNodes);
        else
          update(allLinks, allNodes);*/
        updateJustLinks(allTimeLinks)
      }
      else {

        /*if(just_school) {
          var theLinks = copyArray(filteredLinks);
          console.log("LIIINKS")
          console.log(theLinks)
        }
        else
          var theLinks = copyArray(allLinks);*/
        var theLinks = copyArray(allTimeLinks);

        chosenYear = parseInt(chosenYear)
        var yearFilteredLinks = theLinks.filter(function(l) {
          var count = 0
          var collabs = []
          for(var i=0; i<l.collab_title_url_years.length; i++) {
            if(l.collab_title_url_years[i][2] <= chosenYear) {
              collabs.push(l.collab_title_url_years[i]);
              count += 1;

            }
          }
          if(count > 0) {
            console.log("original num_collabs")
            console.log(l.num_collabs)
            l.num_collabs = count;
            console.log("new num_collabs")
            console.log(l.num_collabs);
            l.num_collabs = count;
            l.collab_title_url_years = collabs;
            return true;
          }
          else
            return false

        })
       /* for(var i=0; i<yearFilteredLinks.length; i++) {
          aLink = yearFilteredLinks[i];
          var collabs = aLink.collab_title_url_years
          collabs = collabs.filter(function(c) {
            return c[2] == chosenYear;
          })
          aLink.collab_title_url_years = collabs
        }*/

        theNodes = force.nodes();
        updateJustLinks(yearFilteredLinks)

      } 
        /*var comFilteredLinks = graph.links.filter(function(l) {
        return nodeArray.indexOf(l.source) > -1 && nodeArray.indexOf(l.target) > -1;*/
    });

    function updateJustLinks(newLinks) {
      updateLinks(newLinks);
      force.links(newLinks);
      updateInfoText(newLinks, force.nodes())
      force.resume();
    }

    function copyArray(arr) {
      arrCopy = []
      for(var i=0; i<arr.length; i++) {
        var original = arr[i];
        var objCopy = JSON.parse(JSON.stringify(original));
        objCopy.source = original.source;
        objCopy.target = original.target;
        arrCopy.push(objCopy);
      }
      return arrCopy;
    }


    d3.selectAll(".labelChoice").on('click', function() {
      svg.selectAll(".label").remove();
      var type = d3.select(this).attr("id");
      if(type != "noLabels")
        labeled = true;
      else
        labeled = false;
      addLabels(node, type)
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

    d3.select('#nodeSearch').on("keyup", function() {
      // Clear array of searched nodes
      searchedNodes  = []
      searchText = this.value.toLowerCase();
      d3.selectAll(".nodeCircle").style("stroke", function(d) {
        if(d.name.toLowerCase().indexOf(searchText) != -1 && searchText.length > 0) {
          searchedNodes.push(d)
          //console.log(d);
          //return "orange";
          if(d.fillColour != "#ff7f0e")
            return "#ff7f0e";
          else
            return "#17becf"
        } 
        else
          return "black";
        })
        .style("stroke-width", function(d) {
          if(d.name.toLowerCase().indexOf(searchText) != -1 && searchText.length > 0)
            return "3px";
        });         
    });


    function addMetricHandlers() {
      d3.selectAll(".metricListItem").on("click", function() {
        var listItem = d3.select(this);
        var metric = listItem.attr("id");
        var name = listItem.attr("data-name");
        var descrptn = listItem.attr("data-desc");
        colourByMetric(metric);
        var keyArray = [["white", "least " + name], ["red", "most " + name]];
        makeKey(keyArray);
        lastInfoBox = displayMetricText(metric, name, descrptn)
        lastInfoBox();
        metricView = true;
      });
    }

    addMetricHandlers()

   
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
        d.fillColour = metricColour(d[metric]);
        return metricColour(d[metric]);
      });
    }

    function displayMetricText(metric, name, description) {
        var infoText = description +
                  "<br><br>Below is the " + name + " of the nodes in this graph, ranging from 0 to 1<br> \
                  (note that this metric is calculated for the full graph, including non-school members)<br><br>"
        theNodes = force.nodes()  
        theNodes.sort(function(a, b) {
          return b[metric]-a[metric];
        });
        for(var i=0, len=theNodes.length; i<len; i++) {
          n = theNodes[i]
          infoText += getAuthorNameHtml(n) + n.name + "</span>: " + Math.round(n[metric] * 1000) / 1000 + "<br><br>"
        }
      return function() {

        displayInfoBox(infoText)
        d3.selectAll(".authorName").on("click", function() {
                                        //var sel = d3.select(this);
                                        //var theId = sel.attr("id");
                                        var theId = d3.select(this).attr("id");
                                        displayInfoForThisNode(theId);
                                        highlightPathsForThisNode(theId);
                                          })
                                        .on("mouseover", highlightThisNode)
                                        .on("mouseout", lowlightJustNode);
      }
    }

    function addComHandler() {
      if(currentViz != vizTypes.INTER) {
        d3.select("#community").on("click", function() {
          getCommunities();
        });
      }
    }

    addComHandler();
      /*var circles = d3.selectAll(".nodeCircle").style("fill", function(d) {
        //console.log("COMM NUMBERS")
        //console.log(d.school_com)
        if(just_school)
          return moreColour(d.school_com);
        else
          return moreColour(d.com)
      })*/
      
    function getCommunities() {
      //alert("gettinghere")
      colourByCommunities();
      var keyArray = []
      var commNums = []
      var communityArray = []
      theNodes = force.nodes()
      // Sorting the nodes by community so that colours get attributed in the right order for the key
      theNodes.sort(function(a, b) {
        if(just_school)
          return a.school_com - b.school_com;
        else
          return a.com - b.com;
      })

      for(var i=0, len=theNodes.length; i<len; i++) {
        if(just_school)
          var commNum = theNodes[i].school_com
        else
          var commNum = theNodes[i].com
        //commNum may be false
        if(commNum !== false) {
          if(communityArray[commNum])
            communityArray[commNum].push(theNodes[i]);
          else
            communityArray[commNum] = [theNodes[i],];
        
          if(commNums.indexOf(commNum) < 0) {
            commNums.push(commNum);
            //console.log("community number:")
            //console.log(commNum);
            keyArray.push([moreColour(commNum), "community " + commNum]);
          }
        }
      }
      keyArray.push(["white", "no community"])
      console.log("COMMUNITIES:");
      console.log(communityArray);
      makeKey(keyArray);
      lastInfoBox = displayCommunityText(communityArray);
      lastInfoBox();
      metricView = true;
    }


    function colourByCommunities() {
      var circles = d3.selectAll(".nodeCircle").style("fill", function(d) {
      //console.log("COMM NUMBERS")
      //console.log(d.school_com)
      if(just_school)
        var comNum = d.school_com;

      else
        var comNum = d.com;

      if(comNum !== false)
        return moreColour(comNum);
      else
        return "white";
      })
    }

    function displayCommunityText(arr) {
    
      console.log("ARRRR");
      console.log(arr);
      var infoText = "The authors in the network can be divided into communities based on the patterns of collaboration. Below are the \
                communities for this network.<br><br>"
      // N.B. community numbers start at 1, not 0
      for(var i=1; i<arr.length; i++) {
        infoText += "<strong><span id=\"" + i + "\" class=\"comTitle clickable\">Community " + i + "</strong><br>";
        var thisCommunity = arr[i];
        console.log(thisCommunity);
        for(var j=0; j < thisCommunity.length; j++) {
          var author = thisCommunity[j];
          /*if(just_school) {
            if(author.in_school)
              infoText += getAuthorNameHtml(author) + author.name + "</span><br>";
          }
          else
            infoText += getAuthorNameHtml(author) + author.name + "</span><br>"; */
          infoText += getAuthorNameHtml(author) + author.name + "</span><br>";
        }
        infoText += "<br>";
      }

      return function() {

        displayInfoBox(infoText);
        d3.selectAll(".authorName").on("click", function() {
                                        //var sel = d3.select(this);
                                        //var theId = sel.attr("id");
                                        var theId = d3.select(this).attr("id");
                                        console.log("IDIDIDIIDALL");
                                        console.log(theId);
                                        displayInfoForThisNode(theId);
                                        highlightPathsForThisNode(theId);
                                          })
                                        .on("mouseover", highlightThisNode)
                                        .on("mouseout", lowlightJustNode);


        d3.selectAll(".comTitle").on("click", function() {
          var comNum = d3.select(this).attr("id");
          //showSingleCommunityGraph(comNum);
          showSingleCommunityGraph(arr[comNum]);
          lastInfoBox = singleCommunityText(arr[comNum], comNum);
          lastInfoBox();
          metricView = true;
          colourByCommunities();
          var metricsList = d3.select("#metricsList");
          metricsList.html("<li>No metrics available in this view</li>")
          updateYearChooser();
          //d3.select("#yearDiv").style("visibility", "hidden");
          // TODO comviz is now done by filtering
          //doComViz(comNum);
        });
        d3.selectAll(".comTitle").on("mouseover", function() {
          var comNum = parseInt(d3.select(this).attr("id"));
          console.log("BLUEBLA")
          var theNodes = force.nodes();
          var comNodes = []
          
          for(var i=0; i<theNodes.length; i++) {
            var author = theNodes[i];
            if(just_school) {
              if(author.school_com === comNum)
                comNodes.push(author);
            }
            else {
              if(author.com === comNum)
                comNodes.push(author);
            }
          }
          highlightNodeGroup(comNodes)
        });

        d3.selectAll(".comTitle").on("mouseout", lowlightJustNode)
      }
    }

    // TODO use array filtering to do this instead
    function getNodesInCom(comNum) {
      nodesInCom = []
      theNodes = force.nodes()
      for(var i=0; i<theNodes.length; i++) {
        var author = theNodes[i]
        if(just_school) {
          if(author.school_com == comNum)
            nodesInCom.push(author)
        }
        else {
          if(author.com == comNum)
            nodesInCom.push(author)
        }
      }
      return nodesInCom;   
    }

    function singleCommunityText(comNodes, comNumber) {
      //var comNodes = getNodesInCom(comNumber)
      //console.log("COMNODES");
      //console.log(comNodes);

      if(just_school)
        var allKeywords = graph.graph[1]
      else
        var allKeywords = graph.graph[0]
      console.log("RONALDO");
      console.log(allKeywords[0]);
      kw_lists = allKeywords[1];
      var comKeywordList = []
      for(var i=0; i<kw_lists.length;i++) {
        if(kw_lists[i][0] == comNumber)
          comKeywordList = kw_lists[i][1]
      }
      //console.log(thisComKw);

      return function() {
        var infoText = "<strong>Community " + comNumber + "</strong><br>";
        infoText += "<span class=\"clickable\" id=\"backToFull\">[back to full graph]</span><br>"
        infoText += "<span class=\"clickable\" id= \"singleComTextOption\">[see community keywords]</span><br><br>"
        infoText += "<span id=\"singleComTextArea\">"
        
        var comNames = ""
        /*theNodes = force.nodes()
        for(var i=0; i<theNodes.length; i++) {
          var author = theNodes[i]
          if(just_school) {
            if(author.school_com == comNumber)
              comNames += getAuthorNameHtml(author) + author.name + "</span><br>"
          }
          else {
            if(author.com == comNumber)
              comNames += getAuthorNameHtml(author) + author.name + "</span><br>"
          }
        }*/
        for(var i=0; i<comNodes.length; i++) {
          author = comNodes[i];
          comNames += getAuthorNameHtml(author) + author.name + "</span><br>"
          console.log(comNames)
        }
        infoText += comNames;
        infoText += "</span>"
        
        var comKeywords = ""
        for(var i=0; i<comKeywordList.length; i++) {
          comKeywords += comKeywordList[i] + " | "
        }



        displayInfoBox(infoText);
        
        /*d3.selectAll(".authorName").on("click", function() {
                                        var theId = d3.select(this).attr("id");
                                        console.log("IDIDIDIIDALL");
                                        console.log(theId);
                                        displayInfoForThisNode(theId);
                                        highlightPathsForThisNode(theId);
                                          })
                                        .on("mouseover", highlightThisNode)
                                        .on("mouseout", lowlightJustNode);*/


        addNameListHandlers()
      
                                            
        d3.select("#backToFull").on("click", function() {
          var school = nameText.text()
          if(just_school) {
            update(filteredLinks, filteredNodes);
            allTimeLinks = filteredLinks;
          }
          else {
            update(allLinks, allNodes);
            allTimeLinks = allLinks;
          }
          //colourByCommunities()
          getCommunities()
          d3.select("#metricsList").html(metricsHtml);
          addMetricHandlers();
          addComHandler();
          updateYearChooser();
        });

        d3.select("#singleComTextOption").on("click", function() {
          var textArea = d3.select("#singleComTextArea")
          var currentText = textArea.html()
          var option = d3.select("#singleComTextOption")
          if(currentText == comNames) {
            textArea.html(comKeywords)
            option.html("[see community authors]");
          }
          else {
            textArea.html(comNames)
            addNameListHandlers()
            option.html("[see community keywords]");
          }

        });

        //var theNodes = force.nodes()
       /* var theLinks = force.links()
        var comFilteredLinks = graph.links.filter(function(l) {
          if(just_school)
            return l.source.school_com == comNumber && l.target.school_com == comNumber;
          else
            return l.source.com == comNumber && l.target.com == comNumber;
        });
        // This gets just the nodes that are in this community
        var comFilteredNodes = graph.nodes.filter(function(n) {
          if(just_school)
            return n.school_com == comNumber;
          else
            return n.com == comNumber;
        });
        update(comFilteredLinks, comFilteredNodes)*/
      }
    }

    // TODO this doesn't work because nodes in collab graphs don't have keywords
    // Do this outside - add keywords as attribute of communities in networkx graph (e.g. 20 kw each)
    function getComKeywords(comNodes) {
      allKeywords = {}
      for(var i=0; i<comNodes.length; i++) {
        // Get keyword array
        authorKw = comNodes[i].keywords;
        for(var j=0; j<authorKw.length; j++) {
          var kw = authorKw[j];
          if(allKeywords.hasOwnProperty(kw))
            allKeywords.kw += 1;
          else
            allKeywords.kw = 1;
        }
      }

      keywordText = ""
      for(var prop in allKeywords) {
        if(allKeywords.hasOwnProperty(prop))
          keywordText += prop + " ";
      }
      console.log("KEyWORDS");
      console.log(keywordText);

    }



    function addNameListHandlers() {
      d3.selectAll(".authorName").on("click", function() {
                                  var theId = d3.select(this).attr("id");
                                  console.log("IDIDIDIIDALL");
                                  console.log(theId);
                                  displayInfoForThisNode(theId);
                                  highlightPathsForThisNode(theId);
                                    })
                                  .on("mouseover", highlightThisNode)
                                  .on("mouseout", lowlightJustNode);                    
    }

    function showSingleCommunityGraph(nodeArray) {
      //var theNodes = force.nodes()
      var theLinks = force.links()
      /*var comFilteredLinks = graph.links.filter(function(l) {
        if(just_school)
          return l.source.school_com == comNumber && l.target.school_com == comNumber;
        else
          return l.source.com == comNumber && l.target.com == comNumber;
      });*/

      var comFilteredLinks = graph.links.filter(function(l) {
        return nodeArray.indexOf(l.source) > -1 && nodeArray.indexOf(l.target) > -1;
      })
      // This gets just the nodes that are in this community
      /*var comFilteredNodes = graph.nodes.filter(function(n) {
        if(just_school)
          return n.school_com == comNumber;
        else
          return n.com == comNumber;
      });*/
      update(comFilteredLinks, nodeArray)
      allTimeLinks = comFilteredLinks;
      d3.selectAll(".keyCircle").remove();
      d3.selectAll(".keyText").remove();
    }


    d3.selectAll(".colourChoice").on("click", function() {
      if(currentViz != vizTypes.SHORTEST && currentViz != vizTypes.SINGLE)
        metricView = false;
      var choice = d3.select(this).attr("id");
      console.log("the choice was" + choice)
      if(choice == "defaultColours")
        colourByDefault();
      else if(choice == "schoolColours")
        colourBySchool();
    });

  // TODO make key in here so don't have to change colours in both places if colours change
    function colourByDefault() {
      console.log("COLOUR BY DEFAULT");
      console.log(currentViz)
      var chosenColour;
      d3.selectAll(".nodeCircle").style("fill", function(d, i) {
        //return colors(i);
        if(currentViz == vizTypes.AUTHOR_COLLAB || currentViz == vizTypes.SIMILARITY) {
          if(d.in_school)
            chosenColour = multiColour(inSchoolColour);
          else {
            console.log(d.name)
            chosenColour = multiColour(nonSchoolColour);
          }
        }

        else if(currentViz == vizTypes.SHORTEST) {
          if(d.isSource)
            chosenColour = "#1f77b4";
          else if(d.isTarget)
            chosenColour = "#d62728";
          else
            chosenColour = "#2ca02c";
        }

        else if(currentViz == vizTypes.SINGLE) {
          if(d.centre)
            chosenColour = multiColour(0);
          else
            chosenColour = multiColour(d.hops);
        }

        else if(currentViz == vizTypes.INTER)
          chosenColour = moreColour(d.name)

        else if(currentViz == vizTypes.TERMSEARCH) {
          if(d.isTerm)
            chosenColour = "white";
          else {
            var randint = Math.floor(Math.random() * 10);
            chosenColour = multiColour(randint);
          } 
        }

        else
          chosenColour = multiColour(d);

        // Give the datum a fillColour attribute to make this easier to access later (used when deciding what colour 
        // to use for highlighting)
        d.fillColour = chosenColour;
        return chosenColour;
      });

      updateKey()
    }

    function colourBySchool() {
      console.log("COLOURS");
      var keyArray = []
      var schools = []
      d3.selectAll(".nodeCircle").style("fill", function(d) {
        if(d.school) {
          console.log(d.school);
          if(schools.indexOf(d.school) < 0) {
            console.log(d.school)
            schools.push(d.school);
            keyArray.push([moreColour(d.school), d.school])
          }
          chosenColour = moreColour(d.school);
        }
        else {
          chosenColour = "white";
        }
        d.fillColour = chosenColour;
        return chosenColour;
      });
      keyArray.push(["white", "School not known"]);
      makeKey(keyArray);
    }


    d3.select("#shortest").on("click", function() {
      lastInfoBox = shortestPathBox();
      lastInfoBox();
    });

    // TODO using a global variable here as a quick fix, please revise
    // e.g. put this outside startitup
    shortestPathBox = function(errorType, errorMessage) {
      return function() {
        var info = "Find the shortest path between two authors anywhere within the university.<br> Please enter the name or, for more accurate \
            results, the unique Enlighten numbers of the source and target authors. You can find out an author's identifier by checking their \
            url <a href=\"http://eprints.gla.ac.uk/view/author/\" target=\"_blank\">here</a><br><br><input type=\"text\" id=\"sourceInput\" \
            placeholder=\"source\"/><br><br><span id=\"sourceCandidates\" data-input=\"sourceInput\"></span> \
            <input type=\"text\" id=\"targetInput\" placeholder=\"target\"/><br><br> \
            <span id=\"targetCandidates\" data-input=\"targetInput\"></span><button type=\"button\" id=\"shortestButton\">Submit</button><br>"

        /*if(errorType == SHORTESTPATHERROR)
          info += "<br>" + errorMessage + "<br>";*/
          info += "<span id=\"shortestError\"></span>"

        info += "<br>You can also find the longest shortest path for an author. How far do their connections go?<br> \
                <br><input type=\"text\" id=\"longestInput\" \
                placeholder=\"source\"/><br><br><span id=\"longestCandidates\" data-input=\"longestInput\"></span> \
                <button type=\"button\" id=\"longestButton\">Submit</button><br><br>"

        /*if(errorType == LONGESTPATHERROR)
          info += errorMessage*/
        info += "<span id=\"longestError\"></span>"

        displayInfoBox(info);
        d3.select("#shortestButton").on("click", getShortest);
        d3.select("#sourceInput").on("keyup", function() {
          if(d3.event.keyCode == 13)
            getShortest();
        });
        d3.select("#targetInput").on("keyup", function() {
          if(d3.event.keyCode == 13)
            getShortest();
        })
        d3.select("#longestButton").on("click", getLongest);
        
        d3.select("#longestInput").on("keyup", function() {
          if(d3.event.keyCode == 13)
            getLongest();   
        })
      }
    }

    d3.select("#single").on("click", function() {
      lastInfoBox  = singleAuthorBox();
      lastInfoBox();
    })

    singleAuthorBox = function(errorMessage) {
      return function() {
        var info = "Display a graph where everyone is directly or indirectly connected to an author.<br> Please enter the name or, for more \
            accurate results, the unique Enlighten number \
            of the author whose graph you want to see. You can find out an author's identifier by checking their \
            url <a href=\"http://eprints.gla.ac.uk/view/author/\" target=\"_blank\">here</a><br><br><input type=\"text\" id=\"singleInput\" \
            placeholder=\"source\"/><br><br> \
            <span id=\"singleCandidates\" data-input=\"singleInput\"></span> \
            Choose how far you want the graph to reach (up to 3 hops)<br><br><input type=\"number\" id=\"cutoffInput\" min=\"0\" max=\"3\"/> \
            <br><br><button type=\"button\" id=\"singleButton\">Submit</button><br><br>"

        //if(errorMessage)
        info += "<span id=\"singleError\"></span>"

        displayInfoBox(info);
        d3.select("#singleButton").on("click", getSingle);
        d3.select("#singleInput").on("keyup", function() {
          if(d3.event.keyCode == 13)
            getSingle();   
        });
        d3.select("#cutoffInput").on("keyup", function() {
          if(d3.event.keyCode == 13)
            getSingle();   
        });
      }
    }


  } // THIS IS THE END OF STARTITUP


  // Using jquery to make get request to server as was having trouble passing parameters in d3 requests
  // get_json is the url which maps to the django view which loads the json file and returns the data
  function getData(name, type) {
    console.log(name)
    $.get('get_json/', {name: name, type: type}, function(data) {
      graph_data = JSON.parse(data);
      //TODO experimenting with stopping timeout
      //console.log("GRAPHATTRIBS")
      //console.log(graph_data.graph[0])
      startItUp(graph_data);

    });
  }



  var getShortest = function() {
    var sourceInfo = $("#sourceInput").val().toLowerCase();
    var targetInfo = $("#targetInput").val().toLowerCase();
    console.log(sourceInfo);
    console.log(targetInfo);
    if(!sourceInfo || !targetInfo)
      //shortestPathBox(SHORTESTPATHERROR, "please enter both authors");
      d3.select("#shortestError").html("<br>please enter both authors<br>");
    else {
      $.get('shortest_path/', {source: sourceInfo, target: targetInfo}, function(data) {
        //graph_data = JSON.parse(data);
        doShortestViz(data, SHORTESTPATHERROR);
      });
    }
  }

  var getLongest = function() {
    var source = $("#longestInput").val().toLowerCase();
    console.log(source)
    if(!source)
      shortestPathBox(LONGESTPATHERROR, "please enter an author");
    else {
      $.get('longest_path/', {source: source}, function(data) {
          doShortestViz(data, LONGESTPATHERROR);
      });
    }
  }

  function doShortestViz(data, errorType) {
    if(data.error) {
      //shortestPathBox(errorType, data.error);
      if(errorType == SHORTESTPATHERROR)
        d3.select("#shortestError").html("<br>" + data.error + "<br>");
      else if(errorType == LONGESTPATHERROR)
        d3.select("#longestError").html("<br>" + data.error + "<br>");
    }
    else if(data.candidates) {
      //shortestPathBox(errorType, data.candidates[0][0])
      if(data.candidates.source_candidates) {
        var slctn = d3.select("#sourceCandidates");
        displayCandidates(slctn, data.candidates.source_candidates);
      }
      if(data.candidates.target_candidates) {
        var slctn = d3.select("#targetCandidates");
        displayCandidates(slctn, data.candidates.target_candidates);
      }
      if(data.candidates.longest_candidates) {
        var slctn = d3.select("#longestCandidates");
        displayCandidates(slctn, data.candidates.longest_candidates);
      }
    }
    else if(data) {
      currentViz = vizTypes.SHORTEST;
      var sourceName = "";
      var targetName = "";
      for(var i=0; i<data.nodes.length; i++) {
        if(data.nodes[i].isSource) {
          sourceName = data.nodes[i].name;
        }
        if(data.nodes[i].isTarget) {
          targetName = data.nodes[i].name;
        }
      }
      console.log(sourceName)
      nameText.text(sourceName + " to")
      typeText.text(targetName)
      lastInfoBox = shortestPathBox();
      lastInfoBox();
      metricView = true;

      var metricsList = d3.select("#metricsList");
      metricsList.html("<li>No metrics available for shortest path graph</li>")
      // TODO in this case do not have to JSON.parse data - find out why
      startItUp(data);
    }
    else {
      shortestPathBox(error);
    }
  }

  function displayCandidates(sel, candidates) {
    var info = "Did you mean:<br><br>"
    for(var i=0; i<candidates.length; i++) {
      var name = candidates[i].name;
      if(candidates[i].school)
        var school = candidates[i].school;
      else
        var school = "school not known";
      var id = candidates[i].id;
      var pos = sel.attr("id");
      var input = sel.attr("data-input")
      info += "<span class=\"candidate clickable\" id=\"" + id + "\" data-pos=\""  + pos + "\" data-input=\"" + input + "\">" + name + "</span> \
      <br>(" + school + ")<br><br>"
    }
    sel.html(info);
    d3.selectAll(".candidate").on("click", function() {
      var authorId = d3.select(this).attr("id");
      // data-pos holds the id of the selection (sourceCandidates or targetCandidates) in which this candidate element is positioned
      // need to keep this data somewhere as if we just use the sel argument to get it, it will use the last value of sel passed,
      // which would always be targetCandidates if there are in fact target candidates present
      var pos = d3.select(this).attr("data-pos");
      var input = d3.select(this).attr("data-input")
      $("#" + input).val(authorId);
      d3.select("#" + pos).html("");
    });
  }

  var getSingle = function() {
    //metricView = false;
    var authorInfo = $("#singleInput").val().toLowerCase();
    var cutoff = $("#cutoffInput").val()
    if(!authorInfo)
      d3.select("#singleError").html("Please enter an author");
    else if(!cutoff || cutoff < 0 || cutoff > 3)
      d3.select("#singleError").html("Please enter a number betwen 0 and 3");
    else {
        $.get('author_search/', {author: authorInfo, cutoff: cutoff}, function(data) {
          console.log("SINGLEERROR");
          console.log(data);
          if(data.error)
            d3.select("#singleError").html(data.error);
          else if(data.candidates) {
            console.log("CANDIDATES")
            console.log(data.candidates)
            var slctn = d3.select("#singleCandidates");
            displayCandidates(slctn, data.candidates)
            //COMPLETE
          }

          else if(data) {
            currentViz = vizTypes.SINGLE
            var name;
            for(var i=0; i<data.nodes.length; i++) {
              if(data.nodes[i].centre) {
                name = data.nodes[i].name;
              }
            }
            nameText.text(name);
            typeText.text("cutoff of " + cutoff);
            startItUp(data)

            lastInfoBox = singleAuthorBox();
            lastInfoBox();
            metricView = true;
            //d3.selectAll(".metricsMenu").style("visibility", "hidden");
            var metricsList = d3.select("#metricsList");
            metricsList.html("<li>No metrics available for single author graph</li>")
            
          }
        // TODO do we need this else to catch other situations?
        else {
          singleAuthorBox(true);
        }
      });
    }
  }


  /*function doComViz(comNumber) {
    //alert(comNumber);
    var currentSchool = nameText.text()
    //alert(currentSchool)
    $.get("community_viz/", {"school":currentSchool, "com_num": comNumber, "just_school":just_school}, function(data) {
      console.log(data)
      startItUp(data);
      //singleCommunityText(comNumber)
    });
  }*/



  d3.selectAll(".collabListItem").on("click", function() {
    metricView = false;
    var type = d3.select(this).attr("data-type");
    var name = d3.select(this).attr("data-name");
    var nmtext = d3.select(this).attr("data-nametext");
    var tptext = d3.select(this).attr("data-typetext");

    if(name == "Inter School")
      currentViz = vizTypes.INTER;
    else if(type == "similarity2")
      currentViz = vizTypes.SIMILARITY
    else
      currentViz = vizTypes.AUTHOR_COLLAB;

    //display background text
    nameText.text(nmtext)
    typeText.text(tptext)
    //Get the new data
    getData(name, type);

    d3.select("#metricsList").html(metricsHtml);

    d3.select("#infoArea").style("visibility", "hidden");  
    inSchoolColour = Math.floor(Math.random() * 10)
    nonSchoolColour = Math.floor(Math.random() * 10)
    while(inSchoolColour == nonSchoolColour)
      nonSchoolColour = Math.floor(Math.random() * 10)
  });

  /*d3.selectAll(".simListItem").on("click", function() {

  })*/


  /*d3.select("#about").on("click", function() {
    displayInfoBox(introText);
  });*/


  function displayInfoBox(text) {
    d3.select("#infoArea")
    .html(close + text)
    .style("visibility", "visible");

    d3.select("#close").on("click", function() {
      d3.select("#infoArea").style("visibility", "hidden");
    });

    $("#infoArea").draggable();
    $("#infoArea").scrollTop(0);    
  }


  d3.select("#kwSearch").on("keyup", function() {
    if(d3.event.keyCode == 13) {
      var query = this.value
      console.log(query)
      $.get('kw_search/', {query: query}, function(data) {
        //alert("made request");
        console.log("THEDAAAAAAAAAAAAATA");
        console.log(data);
        currentViz = vizTypes.TERMSEARCH;
        nameText.text(query);
        typeText.text("keyword search");
        d3.select("#infoArea").style("visibility", "hidden");
        d3.selectAll(".keyCircle").remove();
        d3.selectAll(".keyText").remove();

        startItUp(data)
      });
    }
  });

  //Initial Configuration
  displayInfoBox("The graph on the left is the collaboration network for the School \
                  of Computing Science. The nodes represent authors, who are linked if they have co-authored a paper together.<br><br> \
                  You can see the collaboration graphs for other schools within the University of Glasgow, and for single authors, by exploring \
                  the options on the top menu.");
  getData("School of Computing Science", "collab");
  nameText.text("School of Computing Science");
  typeText.text("collaboration network");


}());
