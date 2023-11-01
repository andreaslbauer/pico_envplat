

var viewportWidth  = document.documentElement.clientWidth;

// set the dimensions and margins of the graph
var margin = {top: 10, right: 60, bottom: 30, left: 30},
    width = viewportWidth - margin.left - margin.right,
    height = 400 - margin.top - margin.bottom;

// append the svg object to the body of the page
var svg = d3.select("#chart")
  .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("transform",
          "translate(" + margin.left + "," + margin.top + ")");


function drawGraph(tag, data) {
 // Add X axis --> it is a date format
  var x = d3.scaleTime()
    .domain(d3.extent(data, function(d) { return d.TimeStamp; }))
    .range([ 0, width ]);
  svg.append("g")
    .attr("transform", "translate(0," + height + ")")
    .call(d3.axisBottom(x));

  // Add Y axis
  var y = d3.scaleLinear()
    .domain([0, d3.max(data, function(d) { return +d.Temp; })])
    .range([ height, 0 ]);

  svg.append("g")
    .call(d3.axisLeft(y));

  console.log(data);

  // Add the line
  svg.append("path")
    .datum(data)
    .attr("fill", "none")
    .attr("stroke", "steelblue")
    .attr("stroke-width", 1.5)
    .attr("d", d3.line()
      .x(function(d) { return x(d.TimeStamp) })
      .y(function(d) { return y(d.Temp) })
      )
    }
}

//Read the data
var url = "/shorttermdata"
fetch(url)
    .then(function(response){
        var data = response.json();
        return data
    })
    .then(function(data){
        //console.log(data);
        for (var i = 0, l = data.length; i < l; i++) {
           var obj = data[i];
           obj['TimeStamp'] = new Date(Date.parse(obj.DateTime));
        }

        drawGraph("#graph", data);
     )
    }
