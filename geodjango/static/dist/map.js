function op_layers(map, options) {

    var osm = 'http://{s}.tile.openstreetmap.org/{z}{y}{x}.png';

    var dataset = new L.GeoJSON.AJAX("{% url 'data' %}");
    dataset.addTo(map);

    var baseLayers = {
        "OpenStreetMap": osm
    };        
    var groupeOverlays ={
        "Layers": {
            "RINF": dataset  
        }
    };               
    L.control.groupedLayers(baseLayers,groupeOverlays).addTo(map);
}

