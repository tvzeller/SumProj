
(function() {

  // To be used as the width and height of the SVG visualisation area
  var width = 1000;
  var height = 600;

  // JS style enums - https://stijndewitt.wordpress.com/2014/01/26/enums-in-javascript/
  var vizTypes = {
    AUTHOR_COLLAB: 1,
    SIMILARITY: 2,
    SHORTEST: 3,
    SINGLE: 4,
    INTER: 5,
    TERMSEARCH: 6,
    SINGLECOM: 7,
  }

  // Start with author collaboration graph as default on page load
  var currentViz = vizTypes.AUTHOR_COLLAB

  // lastInfoBox is set to a function and called when user clicks outside a node, deselecting any selected nodes.
  // The function will either display the last info text that was displayed (e.g. info about a centrality metric or communities) or
  // simply hide any text that was there (which would be info on the node that was selected).
  // As a default, lastInfoBox is set to a function which hides the info text. 
  var lastInfoBox = function() {
    d3.select("#infoArea").style("visibility", "hidden")
  }

  // To be used to stop simulation after a certain amount of time
  var freezeTimeOut;

  // OPTIONS
  // Variables to keep track of whether the visualisation is static or not, and whether nodes are labelled
  var frozen = false;
  var labeled = false;
  
  // Alternative texts displayed on colour button
  var defaultColourText = "use default colours";
  var schoolColourText = "colour by school";

  // Used to avoid dragging being treated like a click
  var downX;
  var downY;

  // Array to keep track of which nodes have been searched for in the graph - to keep them highlighted
  var searchedNodes = []

  // In a single author collab graph, user can select number of hops away from author to see.
  // This keeps track of that number so it can be used in several places
  var numHops;

  // Pseudo-constants to avoid using magic numbers - indicate where to display any error message in the shortest path info text area
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
                    .attr("y", "5%")
                    .attr("class", "displayText")

  var typeText = svg.append("text")
                    .attr("x", 0)
                    .attr("y", "9%")
                    .attr("class", "displayText")

  var nodeCountText = svg.append("text")
                    .attr("x", 0)
                    .attr("y", "13%")
                    .attr("class", "numText");               

  var edgeCountText = svg.append("text")
                     .attr("x", 0)
                    .attr("y", "16%")
                    .attr("class", "numText");

  var keyStartY = height/2.3

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

    var allTimeLinks;

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
      //allTimeLinks = filteredLinks;
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
    }


    // Create a map indicating whether 2 nodes are adjacent, to make it faster to check this when necessary
    // This is used when highlighting paths and neigbours
    // idea from Mike Bostock - http://stackoverflow.com/a/8780277
    var neighboursMap = {}
    for(var i=0; i < allLinks.length; i++) {
      neighboursMap[allLinks[i].source.id + "," + allLinks[i].target.id] = 1;
      neighboursMap[allLinks[i].target.id + "," + allLinks[i].source.id] = 1;
    }

    // Uses neigbours map to check whether two nodes are adjacent in graph
    function neighbours(n1, n2) {
      return neighboursMap[n1.id + "," + n2.id];
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

      // allTimeLinks is used for this so that link width is relative to the maximum collaborations in the non year-filtered graph,
      // so that it is possible to see changes in link width through time
      if(allTimeLinks.length > 0 && allTimeLinks[0].num_collabs != undefined) {
        // Get the maximum number of collaborations
        maxCollabs = Math.max.apply(Math, allTimeLinks.map(function(l){
          return l.num_collabs;
        }));
        // Get the minimum number of collaborations
        minCollabs = Math.min.apply(Math, allTimeLinks.map(function(l){
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
        maxSize = Math.max(Math.min(35, 1000/nodes.length), 8);
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
          if(currentViz == vizTypes.AUTHOR_COLLAB || currentViz == vizTypes.SIMILARITY || currentViz == vizTypes.SINGLECOM && d.paper_count != undefined)
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
            // The search term will have isTerm set to true
            if(d.isTerm)
              return 30;
            else
              return 15;
          }
          // In all other cases default size is 10
          else
            return 10;
        })
        .style("stroke", "black"),

        // Call method to colour the nodes
        colourByDefault();

      // Add labels by default to search and shortest path visualisations
      if(currentViz == vizTypes.TERMSEARCH || currentViz == vizTypes.SHORTEST)
        addLabels(nodeG, "nameLabels");
      else {
        // If labels are off, change text of labelbutton
        d3.select("#labelButton").html("turn on labels");
        labeled = false;
      }

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
      var labelText = sel.append("text")
                    .text(function(d) { 
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
                     .attr("class", "label");

      addLabelAttribs(labelText);
      labeled = true;
      d3.select("#labelButton").html("turn off labels");
    }

    // Function to add style attributes to labels
    function addLabelAttribs(labelText) {
      labelText.attr("font-size", "8px")
        .attr("font-family", "sans-serif")
        .attr("dy", ".35em")
        .attr("text-anchor", "middle")
        .attr("font-weight", "bold")
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
        // Get the name of central node (the author whose graph it is)
        var name = "";
        for(var i=0; i<currentNodes.length; i++) {
          if(currentNodes[i].centre)
            name = currentNodes[i].name;
        }
        var a = [[multiColour(0), name],];

        // Rest of nodes are coloured according to distance from central node, so make
        // key accordingly
        //numHops = $("#cutoffInput").val()
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

      else
        var a = [];
      // Finally call makeKey, passing it the array
      makeKey(a)
    }

    // Function to draw the colour key
    function makeKey(arr) {
      //First remove existing key
      d3.selectAll(".keyCircle").remove();
      d3.selectAll(".keyText").remove();
      // Adjust size of the key based on number of elements
      if(arr.length > 12) {
        var radius = 3.5;
        var textSize = 7.5;
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

    // Function to highlight node when hovering by increasing the width of its stroke
    highlightJustNode = function(d) {
      d3.selectAll(".nodeCircle").style("stroke-width", function(circ) {
        // Stroke is wider (3px) if circ is the hovered node or if node has been searched for (so is in searchedNodes array)
        if(d == circ || searchedNodes.indexOf(circ) != -1)
          return "3px";
      });
    }

    // Function to highlight a group of nodes (used to highlight a community when hovering over community name)
    // Takes array of nodes to be highlighted
    function highlightNodeGroup(arr) {
      d3.selectAll(".nodeCircle").style("stroke-width", function(circ) {
        for(var i=0; i<arr.length; i++) {
          theNode = arr[i];
          if(circ==theNode)
            return "3px";
        }
      });
    }

    // Keeps the stroke of any searched node wider, all other nodes revert to thinner stroke
    lowlightJustNode = function(d) {
      d3.selectAll(".nodeCircle").style("stroke-width", function(circ) {
        if(searchedNodes.indexOf(circ) != -1)
          return "3px";
      });
    }

    // Function to highlight a node, its neighbours and links between them
    highlight = function(d) {
      // Remove any labels attached when previously highlighting another node
      d3.selectAll(".singleLabel").remove()
      // Change the colour or links incident to node
      link.style("stroke", function(l) {
        if (l.source == d || l.target == d) {
          if(currentViz == vizTypes.SIMILARITY && !l.areCoauthors)
            return "#2ca02c";
          else
            return "#FF3030";
        }
        else
          return getLinkColour(l);
      })
      // Reduce opacity of irrelevant links
      .style("opacity", function(l) {
        if (l.source == d || l.target == d)
          return 1.0
        else
          return 0.15
      });

      // Reduce opacity of irrelevant nodes
      node.style("opacity", function(o) {
        if (neighbours(d, o))
          return 1.0
        else if(d==o)
          return 1.0
        else
          return 0.15
      });

      // If the whole graph is not labeled, add a name label to the clicked node
      if(!labeled) {
        theLabel = d3.selectAll(".node").append("text")
                              .attr("class", "singleLabel")
                              .text(function(n) {
                              if(n==d)
                                return n.name;
                            });

        addLabelAttribs(theLabel);                        
      }
    }

    // De-highlights nodes when a node is deselected
    var lowlight = function(d) {
      link.style("stroke", function(l) {
        return getLinkColour(l);
      })
      .style("opacity", 1.0);

      node.style("opacity", 1.0);
     
      d3.selectAll(".singleLabel").remove()
    }

    // Attach a click event handler to whole of visualisation area to deselect a selected node
    // Check if click was on a node - if not, de-highlight all the nodes
    d3.select("#svgArea").on("click", function() {
      var coords = d3.mouse(this);
      // Get x and y coordinates of mouse click
      var xClick = coords[0];
      var yClick = coords[1];
      var onCircle = false;

      // Iterate over nodes, get their coordinates and check if click was on node
      for(var i=0; i<node[0].length; i++) {
        var xNode = node[0][i].__data__.x
        var yNode = node[0][i].__data__.y
        // Get radius of circle element
        var radius = d3.select(node[0][i].firstElementChild).attr("r");
        //Code to check if click is within circle from http://stackoverflow.com/a/16792888
        onCircle = Math.sqrt((xClick - xNode)*(xClick - xNode) + (yClick - yNode) * (yClick - yNode)) < radius
        if(onCircle)
          break;
      }
      // Click was not on any circle
      // De-highlight any highlighted nodes and bring up the last info text (which will be blank in some cases)
      if(!onCircle) {
        lowlight();
        lastInfoBox();
      }
    });
  
    // Used when user clicks on a node, displays list of the node's collaborators or authors with similar keywords (if similarity graph)
    var showCollabInfo = function(d) {
      var info = getAuthorNameHtml(d) + "<strong>" + d.name + "</strong></span></br></br>"
      
      if(currentViz == vizTypes.SIMILARITY) {
        info += "Keywords:<br><br>";
        // TODO not using keyword scores for anything - pass just keywords?
        keyword_scores = d.keywords;
        just_keywords = ""
        for(var i=0; i<keyword_scores.length; i++)
          just_keywords += keyword_scores[i][0] + " "

        info += just_keywords + "<br><br>";
        info += "Researchers with keywords in common:<br><br>"
      }
      else if(currentViz != vizTypes.TERMSEARCH)
        info += "Collaborators:</br></br>";

      // Make array of the clicked node's incident links
      var connections = []
      link.each(function(l) {
        if(l.source == d || l.target == d) {
          connections.push(l)
        }
      });
          
      // Sort the links by number of collaborations so can list them in order
      connections.sort(function(a, b) {
        return (b.num_collabs - a.num_collabs) 
      });
      
      // Make list of collaborators; if clicked node is the link's source, collaborator is target and vice versa
      for(var i=0; i<connections.length; i++) {
        var con = connections[i]
        // Give the element representing number of collaborations an id made up of the link's source and target ids, so
        // that the link object can be identified from the number element
        if(d == con.source)
          info += getAuthorNameHtml(con.target) + con.target.name + "</span> (<span class=\"clickable numCollabs\" id=\"" + 
            con.source.id + "-" + con.target.id + "\">" + con.num_collabs + "</span>)</br></br>"
        else
          info += getAuthorNameHtml(con.source) + con.source.name + "</span> (<span class=\"clickable numCollabs\" id=\"" + 
            con.source.id + "-" + con.target.id + "\">" + con.num_collabs + "</span>)</br></br>"
      }

      if(connections.length == 0)
        info += "none"

      // Display the information
      displayInfoBox(info);
   
      // Attach click handlers to the names of collaborators so can select node by clicking within list, highlight node on hover
      addNameListHandlers();

      // Collaborators get collaboration/similarity number next to name, attach click handler to display collab titles / similar keywords
      if(currentViz == vizTypes.SIMILARITY)
        d3.selectAll(".numCollabs").on("click", showKeywords);
      else
        d3.selectAll(".numCollabs").on("click", showTitles);
    }

    // Function to display collaboration titles between two nodes
    function showTitles() {
      // Get id of number which was clicked
      var elemId = this.id;
      // Iterate over links to get the link which corresponds to the number which was clicked
      // Once found, make list out of the collaboration titles link attribute
      link.each(function(l) {
        if(l.source.id + "-" + l.target.id === elemId) {
          var title_urls = l.collab_title_url_years;

          // Sort the paper titles by date, latest first
          title_urls.sort(function(a, b) {
            // The year of the collab is at index 2 of the title_url array for each paper
            return b[2] - a[2];
          });

          var titleString = "Papers connecting <strong>" + getAuthorNameHtml(l.source) + l.source.name + 
          "</span></strong> and <strong>" + getAuthorNameHtml(l.target) + l.target.name + "</span></strong><br><br>";
          
          for(var i = 0; i < title_urls.length; i++) {
            var title = title_urls[i][0];
            var url = title_urls[i][1];
            var year = title_urls[i][2]

            titleString += title + " (" + year + ")<br><a href=\"" + url + "\" target=\"_blank\">link</a><br><br>"

          }
          
          displayInfoBox(titleString);
          // Event handlers added to author and collaborator name, so can go back to full list of collaborators or
          // select collaborator to view their collaborators
          addNameListHandlers();
        }
      });
    }

    // Function to display the keywords which authors have in common
    function showKeywords() {
      var elemId = this.id;
      // Iterate through links to get link corresponding to clicked number
      link.each(function(l) {
        if(l.source.id + "-" + l.target.id === elemId) {
          var keywords = l.sim_kw;

          var titleString = "<strong>Keywords connecting " + getAuthorNameHtml(l.source) + l.source.name + 
          "</span> and " + getAuthorNameHtml(l.target) + l.target.name + "</span></strong><br><br>";
          
          for(var i = 0; i < keywords.length; i++)
            titleString += keywords[i] + "<br><br>"
          
          displayInfoBox(titleString);
          addNameListHandlers();
        }
      });
    }

    // Function to add event handlers to author names displayed in info text area
    function addNameListHandlers() {
      // The author names have an id corresponding to the id of the node, so the node can be found from the name text element
      d3.selectAll(".authorName").on("click", function() {
                                  var theId = d3.select(this).attr("id");
                                  displayInfoForThisNode(theId);
                                  highlightPathsForThisNode(theId);
                                    })
                                  .on("mouseover", highlightThisNode)
                                  .on("mouseout", lowlightJustNode);                    
    }

    //Helper function to produce the html for displaying an author name in info text area
    function getAuthorNameHtml(theNode) {
      return "<span class=\"clickable authorName\" id=\"" + theNode.id + "\">"
    }

    var displayInfoForThisNode = function(anId) {
        var theNode = getNodeFromId(anId);
        showCollabInfo(theNode);
    }

    var highlightThisNode = function() {
      var storedId = d3.select(this).attr("id");
      var theNode = getNodeFromId(storedId);
      highlightJustNode(theNode)
    }

    var highlightPathsForThisNode = function(anId) {
      var theNode = getNodeFromId(anId);
      highlight(theNode)
    }

    //Used to find a node object from it's ID
    function getNodeFromId(nodeId) {
      var theNodes = force.nodes();
      for(var i=0; i<theNodes.length; i++) {
        if(theNodes[i].id == nodeId)
          return theNodes[i];
      }
    }

    // Make graph static by stopping the force simulation
    // Attach drag event listener to nodes so they can be moved around in static mode
    function freeze() {
      force.stop();
      frozen = true;
      node.call(staticDrag);
      d3.select("#freezeButton").html("defrost graph");
    }

    // Restart simulation
    // Remove the static drag listener and reattach the normal force.drag listener
    function defrost() {
      node.on(".drag", null)
      node.call(force.drag);
      force.resume();
      frozen = false;
    }

    // Used to make graph static (stop the D3 simulation) after certain amount of time
    function setFreezeTimeout(links, nodes) {
      // First clear any currently running timeout
      clearTimeout(freezeTimeOut)
      d3.select("#freezeButton").html("freeze graph");
      frozen = false;
      // This timeout function stops the simulation after a certain amount of time
      var timeToFreeze = Math.min(5000 + (nodes.length * links.length), 15000);
      freezeTimeOut = setTimeout(function() {
        freeze();
      }, timeToFreeze);
    }

    // Function called when new data is obtained from server or when current data is filtered and graph needs to be redrawn
    function update(links, nodes) {
      // Start timer to stop simulation after certain amount of time
      setFreezeTimeout(links, nodes);
      // set allTimeLinks to the full set of links in current view
      allTimeLinks = links;

      // Update the links and nodes visual elements with new data
      updateLinks(links);
      updateNodes(nodes);
      // Change the node count and link count text
      updateInfoText(links, nodes);

      // Formula to set appropriate gravity and charge as a function of the number of nodes
      // and the area
      // based on http://stackoverflow.com/a/9929599
      var k = Math.sqrt(nodes.length / (width * height));
      force.gravity(80 * k)
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
            .linkDistance(function(d) {
              if(currentViz == vizTypes.SHORTEST)
                return 60;
              else if(currentViz == vizTypes.SINGLE) {
                if(d.centre)
                  return 5/k;
                else
                  return 0.5/k
              }

              else
                //return 3;
                return 0.8/k;
            });

      // If visualisation is single author graph, fix author in center of visualisation area
      if(currentViz == vizTypes.SINGLE) {
        for(var i=0; i<nodes.length; i++) {
          if(nodes[i].centre) {
            nodes[i].fixed = true;
            nodes[i].x = width/2
            nodes[i].y = height/2
          }
        }
      }

      // Pass the node and link data to the D3 force layout and start it
      force.nodes(nodes)
            .links(links)
            .start();  
      
      // Call tick function with each tick of the simulation
      force.on("tick", tick);

      updateOptions();
    }

    function updateOptions() {
      /* Display or hide button to toggle non school members and year filter dropdown 
        depending on type of visualisation*/
      if(currentViz == vizTypes.AUTHOR_COLLAB || currentViz == vizTypes.SIMILARITY)
        d3.select("#membersButton").style("visibility", "visible");
      else
        d3.select("#membersButton").style("visibility", "hidden");

      if(currentViz != vizTypes.SIMILARITY) {
        updateYearChooser();
        d3.select("#yearDiv").style("visibility", "visible");
      }
      else
        d3.select("#yearDiv").style("visibility", "hidden");

      if(currentViz == vizTypes.AUTHOR_COLLAB) {
        d3.select("#metricsList").html(metricsHtml);
        addMetricHandlers();
      }
      else
        d3.select("#metricsList").html("<li>No metrics available in this view</li>");
    }

    // Call the update function
    // TODO put this at the end?
    update(currentLinks, currentNodes)

    // Standard function used in D3 visualisations to adjust position of visual elements based on position of
    // corresponding data elements in the force simulation
    // Force simulation is running in background, position of things is changing with each tick
    // In order to see this visually, we need to get the current x and y positions on each tick and update the lines 
    function tick() {
     link.attr("x1", function(d) { return d.source.x; })
          .attr("y1", function(d) { return d.source.y; })
          .attr("x2", function(d) { return d.target.x; })
          .attr("y2", function(d) { return d.target.y; });
      // same with g elements, but these have no x and y, have to be translated
      node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
    }  

    // Add handler to button to toggle between just school members and non-school members
    d3.select("#membersButton").on("click", function() {
      // If current view is just school members (just_school == true), update graph to show everyone             
      if(just_school) {
        just_school = false;
        update(allLinks, allNodes);
        d3.select(this).html("show just school members")
      }
      else {
        // If current view is everyone, update graph to show just school members
        just_school = true;
        update(filteredLinks, filteredNodes)
        d3.select(this).html("show non-school authors")
      }
      // Hide the current info text area
      d3.select("#infoArea").style("visibility", "hidden");
    })

    // Handler for button to stop / start D3 force simulation
    d3.select("#freezeButton").on("click", function() {
      if(frozen) {
        defrost();
        d3.select(this).html("freeze graph");
      }
      else {
        freeze();
      }
    })

    // Function to update the year filter dropdown based on current graph
    function updateYearChooser() {
      theLinks = allTimeLinks;
      // Get the latest year out of all collaborations
      var maxYear = Math.max.apply(Math, theLinks.map(function(l){
        for(var i=0; i<l.collab_title_url_years.length; i++)
          return l.collab_title_url_years[i][2];
      }));

      // Get the earliest year out of all collaborations
      var minYear = theLinks[0].collab_title_url_years[0][2];
      for(var i=0; i<theLinks.length; i++) {
        for (var j=0; j<theLinks[i].collab_title_url_years.length; j++) {
          if(theLinks[i].collab_title_url_years[j][2] < minYear)
            minYear = theLinks[i].collab_title_url_years[j][2];
        }
      }

      // Set the year filter options - all the years from earliest to latest
      yearChooser = d3.select("#yearChooser");
      var options = "<option value=\"all\">all time</option>";
      for(var i=maxYear; i>=minYear; i--) {
        options += "<option value=\"" + i + "\">up to " + i + "</option>"
      }
      yearChooser.html(options)
    }

    // Function to filter graph based on year chosen by user
    d3.select("#yearChooser").on('change', function() {
      chosenYear = this.options[this.selectedIndex].value;

      // If user selected all time, update links using all links
      if(chosenYear === "all")
        updateJustLinks(allTimeLinks)

      // Otherwise filter links according to chosen year
      else {
        // Make copy of all the links so as not to change the properties of the original objects
        var theLinks = copyArray(allTimeLinks);
        chosenYear = parseInt(chosenYear)
        // Filter the links based on chosen year, making array of filtered links
        var yearFilteredLinks = theLinks.filter(function(l) {
          /* Each link has a list of collaborations. Keep only collaborations with date before or equal to chosen year
            and put in new list. 
          */
          var collabs = []
          for(var i=0; i<l.collab_title_url_years.length; i++) {
            if(l.collab_title_url_years[i][2] <= chosenYear)
              collabs.push(l.collab_title_url_years[i]);
          }

          if(collabs.length > 0) {
            // Give link new num_collabs and collab_title_url_years properties
            l.num_collabs = collabs.length;
            l.collab_title_url_years = collabs;
            // Return true so this link is put in yearFilteredLinks
            return true;
          }
          else
            // No collaborations within year range, so return false so this link is excluded
            return false

        })
        // Update with the new filtered links
        updateJustLinks(yearFilteredLinks)
      } 
    });

    // Function to make copy of array of link objects, to be used for filtering links
    function copyArray(linkArr) {
      arrCopy = []
      for(var i=0; i<linkArr.length; i++) {
        var original = linkArr[i];
        // Make deep copy of link object
        var objCopy = JSON.parse(JSON.stringify(original));
        // Set source and target nodes of copied link to object references of original link
        // This is so that the D3 visualisation works and the links stay in correct position in relation to nodes
        objCopy.source = original.source;
        objCopy.target = original.target;
        arrCopy.push(objCopy);
      }
      return arrCopy;
    }

    // Updates just the link objects in the visualisation
    function updateJustLinks(newLinks) {
      var theNodes = force.nodes();
      setFreezeTimeout(newLinks, theNodes);
      // Call updateLinks to update the visual elements
      updateLinks(newLinks);
      // Update the links in the force layout
      force.links(newLinks);
      updateInfoText(newLinks, theNodes);
      // Restart force layout so links get positioned correctly
      force.resume();
      // Change freeze button text since graph is now non-static
      d3.select("#freezeButton").html("freeze graph");
    }

    // Add handler to labels button to add or remove name labels
    d3.select("#labelButton").on('click', function() {
      // If labels are currently on, remove them
      if(labeled) {
        svg.selectAll(".label").remove();
        labeled = false;
        d3.select(this).html("turn on labels");
      }
      // Otherwise add them
      else {
        addLabels(node, "nameLabels");
      }

    });

    // Handler for searching for nodes within graph
    d3.select('#nodeSearch').on("keyup", function() {
      // Clear array of searched nodes
      searchedNodes  = []
      searchText = this.value.toLowerCase();
      // Change outline colour of nodes whose names match search text
      d3.selectAll(".nodeCircle").style("stroke", function(d) {
        if(d.name.toLowerCase().indexOf(searchText) != -1 && searchText.length > 0) {
          searchedNodes.push(d)
          // Ensure that new outline colour is not the same as the node's fill colour
          if(d.fillColour != "#ff7f0e")
            return "#ff7f0e";
          else
            return "#17becf"
        } 
        // Nodes not searched for keep black outline
        else
          return "black";
        })
        // Thicken outline of searched nodes
        .style("stroke-width", function(d) {
          if(d.name.toLowerCase().indexOf(searchText) != -1 && searchText.length > 0)
            return "3px";
        });         
    });

    // Function to add handlers to metric menu options
    // Called each time metrics menu options become available again
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
      });
      addComHandler();
    }


    function addComHandler() {
      if(currentViz != vizTypes.INTER) {
        d3.select("#community").on("click", function() {
          getCommunities();
        });
      }
    }

    // Colours the nodes according to the value of a centrality metric
    function colourByMetric(metric) {
      theNodes = force.nodes()
      // Get maximum centrality metric value out of all nodes
      max = Math.max.apply(Math,theNodes.map(function(n){
        return n[metric]
      }));
      // Get minimum centrality metric value out of all nodes
      min = Math.min.apply(Math,theNodes.map(function(n){
        return n[metric]
      }));
      // Set range domain and range
      metricColour.domain([min, max])
                  .range(["white", "red"]);

      // Change colour of nodes according to their metric value
      d3.selectAll(".nodeCircle").style("fill", function(d) {
        d.fillColour = metricColour(d[metric]);
        return d.fillColour;
      });
    }

    // Prepares info text for a centrality metric
    function displayMetricText(metric, name, description) {
      var infoText = description +
                "<br><br>Below is the " + name + " of the nodes in this graph, ranging from 0 to 1<br> \
                (note that this metric is calculated for the full graph, including non-school members)<br><br>"
      theNodes = force.nodes()  
      // Sort the nodes by value of metric, highest first
      theNodes.sort(function(a, b) {
        return b[metric]-a[metric];
      });
      // Create list of ranked nodes
      for(var i=0, len=theNodes.length; i<len; i++) {
        n = theNodes[i]
        infoText += getAuthorNameHtml(n) + n.name + "</span>: " + Math.round(n[metric] * 1000) / 1000 + "<br><br>"
      }
      // Return a function to display info text area showing prepared text; this function can be set to a variable by calling code
      // and called again to display same information if necessary
      return function() {
        displayInfoBox(infoText);
        addNameListHandlers();
      }
    }
      
    // Function to make an array of arrays, each one a different community of nodes  
    function getCommunities() {
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

      // Nodes have two different community properties - the community computed from the just school members graph, and the
      // community computed from the full graph; get appropriate one
      for(var i=0, len=theNodes.length; i<len; i++) {
        if(just_school)
          var commNum = theNodes[i].school_com
        else
          var commNum = theNodes[i].com
        //commNum may be false if node not in any community (no collaborators)
        if(commNum !== false) {
          // If the node's community is already in outer array, put node into inner array representing the community
          if(communityArray[commNum])
            communityArray[commNum].push(theNodes[i]);
          // Otherwise add a new inner array representing the community, indexed at the community number
          else
            communityArray[commNum] = [theNodes[i],];
          
          // Add to key array to be used to make the community colour key; only add community if not already present
          if(commNums.indexOf(commNum) < 0) {
            commNums.push(commNum);
            keyArray.push([moreColour(commNum), "community " + commNum]);
          }
        }
      }
      keyArray.push(["white", "no community"])
      makeKey(keyArray);
      // Set lastInfoBox to function which displays the text listing the communities
      lastInfoBox = displayCommunityText(communityArray);
      lastInfoBox();
    }

    // Function to colour the nodes according to their community
    function colourByCommunities() {
      var circles = d3.selectAll(".nodeCircle").style("fill", function(d) {
        // Get appropriate community property (just school community or full graph community)
        if(just_school)
          var comNum = d.school_com;
        else
          var comNum = d.com;
        // If node not in any community (no collaborators), it is coloured white
        if(comNum !== false) {
          d.fillColour = moreColour(comNum);
          return moreColour(comNum);
        }
        else {
          d.fillColour = "white";
          return "white";
        }
      });
    }

    // Function to prepare the text listing the communities; takes array of arrays, each sub-array being a community
    function displayCommunityText(arr) {
      var infoText = "The authors in the network can be divided into communities based on the patterns of collaboration. Below are the \
                communities for this network.<br><br>"
      // N.B. community numbers start at 1, not 0
      for(var i=1; i<arr.length; i++) {
        infoText += "<strong><span id=\"" + i + "\" class=\"comTitle clickable\">Community " + i + "</strong><br>";
        var thisCommunity = arr[i];
        for(var j=0; j < thisCommunity.length; j++) {
          var author = thisCommunity[j];
          infoText += getAuthorNameHtml(author) + author.name + "</span><br>";
        }
        infoText += "<br>";
      }

      // Return a function which displays the prepared text and adds necessary event handlers
      return function() {
        displayInfoBox(infoText);
        addNameListHandlers();

        // Handler for when user clicks on a community title - displays single community graph and info
        d3.selectAll(".comTitle").on("click", function() {
          var comNum = d3.select(this).attr("id");
          currentViz = vizTypes.SINGLECOM;
          showSingleCommunityGraph(arr[comNum]);
          lastInfoBox = singleCommunityText(arr[comNum], comNum);
          lastInfoBox();
          colourByCommunities();
        });

        // Handler for highlighting community within full graph when user hovers over community title
        d3.selectAll(".comTitle").on("mouseover", function() {
          var comNum = parseInt(d3.select(this).attr("id"));
          comNodes = getNodesInCom(comNum);
          highlightNodeGroup(comNodes)
        });

        d3.selectAll(".comTitle").on("mouseout", lowlightJustNode)
      }
    }

    // Function to get an array of nodes in a specific community, given the community number
    function getNodesInCom(comNum) {
      var theNodes = force.nodes()
      var nodesInCom = theNodes.filter(function(n) {
        if(just_school)
          return n.school_com == comNum;
        else
          return n.com == comNum;
      });
      return nodesInCom;   
    }

    // Prepares the info text to display with single community graph visualisation
    function singleCommunityText(comNodes, comNumber) {
      // Get the community keywords - they are a property of the graph object in the JSON data
      if(just_school)
        var allKeywords = graph.graph[1]
      else
        var allKeywords = graph.graph[0]

      // The actual arrays of keywords are in an array stored at index 1 of allKeywords
      kw_lists = allKeywords[1];
      var comKeywordList = []
      // Each list of keywords is the second element in an array in which the first element is the community number
      // Get the keywords for this community
      for(var i=0; i<kw_lists.length;i++) {
        if(kw_lists[i][0] == comNumber)
          comKeywordList = kw_lists[i][1]
      }

      // Make the text to display
      var infoText = "<strong>Community " + comNumber + "</strong><br>";
      infoText += "<span class=\"clickable\" id=\"backToFull\">[back to full graph]</span><br>"
      infoText += "<span class=\"clickable\" id= \"singleComTextOption\">[see community keywords]</span><br><br>"
      infoText += "<span id=\"singleComTextArea\">"
      
      var comNames = ""
      for(var i=0; i<comNodes.length; i++) {
        author = comNodes[i];
        comNames += getAuthorNameHtml(author) + author.name + "</span><br>"
      }
      infoText += comNames;
      infoText += "</span>"
      
      var comKeywords = ""
      for(var i=0; i<comKeywordList.length; i++) {
        comKeywords += comKeywordList[i] + " | "
      }

      // Return a function which displays the prepared text
      return function() {
        displayInfoBox(infoText);
        addNameListHandlers()
      
        // Handler for back to full graph option, displays full graph again                                   
        d3.select("#backToFull").on("click", function() {
          var school = nameText.text()
          currentViz = vizTypes.AUTHOR_COLLAB;
          if(just_school) {
            update(filteredLinks, filteredNodes);
          }
          else {
            update(allLinks, allNodes);
          }
          getCommunities()
        });

        // Handler to toggle between displaying names of community members and community keywords
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
      }
    }


    // Displays the visualisation for a graph containing just the nodes in the array passed as argument
    // Used to display single community
    function showSingleCommunityGraph(nodeArray) {
      // Filter full set of links to just links between nodes in the node array
      var theLinks = force.links()
      var comFilteredLinks = graph.links.filter(function(l) {
        return nodeArray.indexOf(l.source) > -1 && nodeArray.indexOf(l.target) > -1;
      })
      // Update the visualisation
      update(comFilteredLinks, nodeArray)
      d3.selectAll(".keyCircle").remove();
      d3.selectAll(".keyText").remove();
    }

    // Event handler for changing node colours using the colour button
    d3.select("#colourButton").on("click", function() {
      // When colours are changed, hide the info text area, since info probably not relevant anymore (e.g. info on centrality metrics)
      if(currentViz != vizTypes.SHORTEST && currentViz != vizTypes.SINGLE && currentViz != vizTypes.SINGLECOM) {
        // Set lastInfoBox function to hide info text area - no info text to display when user deselects a node
        lastInfoBox = function() {
          d3.select("#infoArea").style("visibility", "hidden");
        }
        lastInfoBox();
      }

      var button = d3.select(this);
      if(button.html() === schoolColourText) {
        colourBySchool();
      }
      else if(button.html() === defaultColourText) {
        colourByDefault();
      }
    })

    // Function to colour nodes using default colours based on the type of visualiation
    function colourByDefault() {
      // Change text of colour button 
      d3.select("#colourButton").html(schoolColourText);
      // If in single community mode, colour by communities and return
      if(currentViz == vizTypes.SINGLECOM) {
        colourByCommunities();
        return;
      }

      var chosenColour;
      d3.selectAll(".nodeCircle").style("fill", function(d, i) {

        if(currentViz == vizTypes.AUTHOR_COLLAB || currentViz == vizTypes.SIMILARITY) {
          if(d.in_school)
            chosenColour = multiColour(inSchoolColour);
          else 
            chosenColour = multiColour(nonSchoolColour);
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

    // Function to colour nodes according to what school they are in
    function colourBySchool() {
      d3.select("#colourButton").html(defaultColourText);
      var keyArray = []
      var schools = []
      // Keep track of whether any node in the graph is not in a school - so that "school not known" is added to key
      var nonSchoolPresent = false;
      d3.selectAll(".nodeCircle").style("fill", function(d) {
        if(d.school) {
          if(schools.indexOf(d.school) < 0) {
            schools.push(d.school);
            keyArray.push([moreColour(d.school), d.school])
          }
          chosenColour = moreColour(d.school);
        }
        else {
          chosenColour = "white";
          // Node not in school so change this to true
          nonSchoolPresent = true;
        }
        d.fillColour = chosenColour;
        return chosenColour;
      });
      if(nonSchoolPresent)
        keyArray.push(["white", "School not known"]);

      makeKey(keyArray);
    }

    // Add click event handler to school names in dropdown so user can select school graph
    d3.selectAll(".schoolListItem").on("click", function() {
      // Get school name and type of graph stored as attributes of html element
      var type = d3.select(this).attr("data-type");
      var name = d3.select(this).attr("data-name");
      var nmtext = d3.select(this).attr("data-nametext");
      var tptext = d3.select(this).attr("data-typetext");

      // Change currentViz based on option chosen
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

      // Set lastInfoBox to function which hides the info text area
      lastInfoBox = function() {
        d3.select("#infoArea").style("visibility", "hidden");
      }
      lastInfoBox();
      // Get random colours to use in graph  
      inSchoolColour = Math.floor(Math.random() * 10)
      nonSchoolColour = Math.floor(Math.random() * 10)
      // Ensure non-school colour is different from inSchoolColour
      while(inSchoolColour == nonSchoolColour)
        nonSchoolColour = Math.floor(Math.random() * 10)
    });

    // Event handler for shortest path menu option
    d3.select("#shortest").on("click", function() {
      // Show shortest path info text
      var showPathText = shortestPathBox();
      showPathText();
    });

    shortestPathBox = function() {
      // HTML for shortest path text, including text input boxes to enter author names/ids
      var info = "Find the shortest path between two authors anywhere within the university.<br> Please enter the name or, for more accurate \
          results, the unique Enlighten numbers of the source and target authors. You can find out an author's identifier by checking their \
          url <a href=\"http://eprints.gla.ac.uk/view/author/\" target=\"_blank\">here</a><br><br><input type=\"text\" id=\"sourceInput\" \
          placeholder=\"source\"/><br><br><span id=\"sourceCandidates\" data-input=\"sourceInput\"></span> \
          <input type=\"text\" id=\"targetInput\" placeholder=\"target\"/><br><br> \
          <span id=\"targetCandidates\" data-input=\"targetInput\"></span><button type=\"button\" id=\"shortestButton\">Submit</button><br>"

      // Empty span to display error if necessary
      info += "<span id=\"shortestError\"></span>"

      info += "<br>You can also find the longest shortest path for an author. How far do their connections go?<br> \
              <br><input type=\"text\" id=\"longestInput\" \
              placeholder=\"source\"/><br><br><span id=\"longestCandidates\" data-input=\"longestInput\"></span> \
              <button type=\"button\" id=\"longestButton\">Submit</button><br><br>"

      info += "<span id=\"longestError\"></span>"      

      // Return a function which displays prepared html and adds event handlers to html elements
      return function() {
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

    // Event handler for single author graph menu option
    d3.select("#single").on("click", function() {
      var showSingleText = singleAuthorBox();
      showSingleText();
    })

    singleAuthorBox = function() {
      var info = "Display a graph where everyone is directly or indirectly connected to an author.<br> Please enter the name or, for more \
        accurate results, the unique Enlighten number \
        of the author whose graph you want to see. You can find out an author's identifier by checking their \
        url <a href=\"http://eprints.gla.ac.uk/view/author/\" target=\"_blank\">here</a><br><br><input type=\"text\" id=\"singleInput\" \
        placeholder=\"source\"/><br><br> \
        <span id=\"singleCandidates\" data-input=\"singleInput\"></span> \
        Choose how far you want the graph to reach (up to 3 hops)<br><br><input type=\"number\" id=\"cutoffInput\" min=\"0\" max=\"3\"/> \
        <br><br><button type=\"button\" id=\"singleButton\">Submit</button><br><br>"

        info += "<span id=\"singleError\"></span>"

      // Return function to display prepared html and attach event handlers
      return function() {
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

  } // This is the end of startItUp()



  // Used to get one of the stored JSON graphs (collaboration graphs or keyword similarity graphs)
  // Uses AJAX
  function getData(name, type) {
    // Using jquery to make get request to server as tricky to pass parameters in D3 ajax get request
    // get_json is the url which maps to the django view which loads the json file and returns the data
    $.get('get_json/', {name: name, type: type}, function(data) {
      graph_data = JSON.parse(data);
      // call startItUp with new data
      startItUp(graph_data);

    });
  }

  // Function to get shortest path graph based on authors input by user
  var getShortest = function() {
    // Get input authors
    var sourceInfo = $("#sourceInput").val().toLowerCase();
    var targetInfo = $("#targetInput").val().toLowerCase();
    // If info missing display error message
    if(!sourceInfo || !targetInfo)
      d3.select("#shortestError").html("<br>please enter both authors<br>");
    // Otherwise get the data from the server and pass to function to handle it
    // Second parameter indicates where on the page to display error if data comes back with an error
    else {
      $.get('shortest_path/', {source: sourceInfo, target: targetInfo}, function(data) {
        doShortestViz(data, SHORTESTPATHERROR);
      });
    }
  }

  // Same as getShortest
  var getLongest = function() {
    var source = $("#longestInput").val().toLowerCase();
    if(!source)
      d3.select("#longestError").html("please enter an author");
    else {
      $.get('longest_path/', {source: source}, function(data) {
          doShortestViz(data, LONGESTPATHERROR);
      });
    }
  }

  // Takes data obtained from the server, checks for errors/calls functions to update visualisation
  function doShortestViz(data, errorType) {
    // Data can come back from server with an error message (e.g. author not found)
    if(data.error) {
      if(errorType == SHORTESTPATHERROR)
        d3.select("#shortestError").html("<br>" + data.error + "<br>");
      else if(errorType == LONGESTPATHERROR)
        d3.select("#longestError").html("<br>" + data.error + "<br>");
    }
    // If data has candidates, more than one author matches name input by user, so display all the candidates so user can choose
    else if(data.candidates) {
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
    // If data is OK and authors only have one match, update graph visualisation
    else if(data) {
      currentViz = vizTypes.SHORTEST;
      var sourceName = "";
      var targetName = "";
      // Get the names of source and target to update graph name text
      for(var i=0; i<data.nodes.length; i++) {
        if(data.nodes[i].isSource) {
          sourceName = data.nodes[i].name;
        }
        if(data.nodes[i].isTarget) {
          targetName = data.nodes[i].name;
        }
      }
      nameText.text(sourceName + " to")
      typeText.text(targetName)
      // Set lastInfoBox to function which displays shortest path info text
      lastInfoBox = shortestPathBox();
      lastInfoBox();
      
      // Display new data
      startItUp(data);
    }
  }

  // Called in case response from server indicates that name input by user matches more than one author
  // Displays list of candidates so user can choose one
  function displayCandidates(sel, candidates) {
    var info = "Did you mean:<br><br>"
    // Prepare HTML to display
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
    // Display HTML in the selection passed as parameter
    sel.html(info);
    // Add event handler so that when user clicks on a candidate name, their id is put into the relevant text input to be searched for
    d3.selectAll(".candidate").on("click", function() {
      var authorId = d3.select(this).attr("id");
      // data-pos holds the id of the selection (sourceCandidates or targetCandidates) in which this candidate element is positioned
      // need to keep this data somewhere as if we just use the sel argument to get it, it will use the last value of sel passed,
      // which would always be targetCandidates if there are in fact target candidates present
      var pos = d3.select(this).attr("data-pos");
      var input = d3.select(this).attr("data-input")
      // Put chosen candidate id into input box
      $("#" + input).val(authorId);
      // Erase list of candidates
      d3.select("#" + pos).html("");
    });
  }

  // Function to get and display data for single author graph based on author name input by user
  var getSingle = function() {
    var authorInfo = $("#singleInput").val().toLowerCase();
    var cutoff = $("#cutoffInput").val()
    // If info missing display error message
    if(!authorInfo)
      d3.select("#singleError").html("Please enter an author");
    else if(!cutoff || cutoff < 0 || cutoff > 3)
      d3.select("#singleError").html("Please enter a number betwen 0 and 3");

    // Otherwise, make request to server passing info
    else {
        $.get('author_search/', {author: authorInfo, cutoff: cutoff}, function(data) {
          // If response has error, display it
          if(data.error)
            d3.select("#singleError").html(data.error);
          // If response has multiple author candidates display them
          else if(data.candidates) {
            var slctn = d3.select("#singleCandidates");
            displayCandidates(slctn, data.candidates)
          }

          // Othewise update the visualisation with the new data
          else if(data) {
            currentViz = vizTypes.SINGLE
            // Get name of central node to display
            var name;
            for(var i=0; i<data.nodes.length; i++) {
              if(data.nodes[i].centre) {
                name = data.nodes[i].name;
              }
            }
            nameText.text(name);
            typeText.text("cutoff of " + cutoff);
            // Set numHops variable so that function that makes key can use it
            numHops = cutoff;
            // Set lastInfoBox to function which displays single author graph info text
            lastInfoBox = singleAuthorBox();
            lastInfoBox();

            // Update visualisation
            startItUp(data)   
          }
      });
    }
  }

  // Function to display the info text area. Takes the html string as a parameter and assigns it to the infoArea selection.
  function displayInfoBox(text) {
    d3.select("#infoArea")
    .html(close + text)
    .style("visibility", "visible");

    d3.select("#close").on("click", function() {
      d3.select("#infoArea").style("visibility", "hidden");
    });

    // Makes the infoArea draggable and puts the scroll bar at the top by default
    $("#infoArea").draggable();
    $("#infoArea").scrollTop(0);    
  }

  // Function to get results of keyword search
  d3.select("#kwSearch").on("keyup", function() {
    if(d3.event.keyCode == 13) {
      var query = this.value
  
      $.get('kw_search/', {query: query}, function(data) {
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
