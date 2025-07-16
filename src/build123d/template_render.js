function render(data, div_id, ratio){

    // Initial setup
    const renderWindow = vtk.Rendering.Core.vtkRenderWindow.newInstance();
    const renderer = vtk.Rendering.Core.vtkRenderer.newInstance({ background: [1, 1, 1 ] });
    renderWindow.addRenderer(renderer);

    // iterate over all children children
    for (var el of data){
        var trans = el.position;
        var rot = el.orientation;
        var rgba = el.color;
        var shape = el.shape;

        // load the inline data
        var reader = vtk.IO.XML.vtkXMLPolyDataReader.newInstance();
        const textEncoder = new TextEncoder();
        reader.parseAsArrayBuffer(textEncoder.encode(shape));

        // setup actor,mapper and add
        const mapper = vtk.Rendering.Core.vtkMapper.newInstance();
        mapper.setInputConnection(reader.getOutputPort());
        mapper.setResolveCoincidentTopologyToPolygonOffset();
        mapper.setResolveCoincidentTopologyPolygonOffsetParameters(0.5,100);

        const actor = vtk.Rendering.Core.vtkActor.newInstance();
        actor.setMapper(mapper);

        // set color and position
        actor.getProperty().setColor(rgba.slice(0,3));
        actor.getProperty().setOpacity(rgba[3]);

        actor.rotateZ(rot[2]*180/Math.PI);
        actor.rotateY(rot[1]*180/Math.PI);
        actor.rotateX(rot[0]*180/Math.PI);

        actor.setPosition(trans);

        renderer.addActor(actor);

    };

    renderer.resetCamera();

    const openglRenderWindow = vtk.Rendering.OpenGL.vtkRenderWindow.newInstance();
    renderWindow.addView(openglRenderWindow);

    // Get the div container    
    const container = document.getElementById(div_id);
    const dims = container.parentElement.getBoundingClientRect();

    openglRenderWindow.setContainer(container);

    // handle size
    if (ratio){
        openglRenderWindow.setSize(dims.width, dims.width*ratio);
    }else{
        openglRenderWindow.setSize(dims.width, dims.height);
    };

    // Interaction setup
    const interact_style = vtk.Interaction.Style.vtkInteractorStyleManipulator.newInstance();

    const manips = {
        rot: vtk.Interaction.Manipulators.vtkMouseCameraTrackballRotateManipulator.newInstance(),
        pan: vtk.Interaction.Manipulators.vtkMouseCameraTrackballPanManipulator.newInstance(),
        zoom1: vtk.Interaction.Manipulators.vtkMouseCameraTrackballZoomManipulator.newInstance(),
        zoom2: vtk.Interaction.Manipulators.vtkMouseCameraTrackballZoomManipulator.newInstance(),
        roll: vtk.Interaction.Manipulators.vtkMouseCameraTrackballRollManipulator.newInstance(),
    };

    manips.zoom1.setControl(true);
    manips.zoom2.setScrollEnabled(true);
    manips.roll.setShift(true);
    manips.pan.setButton(2);

    for (var k in manips){
        interact_style.addMouseManipulator(manips[k]);
    };

    const interactor = vtk.Rendering.Core.vtkRenderWindowInteractor.newInstance();
    interactor.setView(openglRenderWindow);
    interactor.initialize();
    interactor.bindEvents(container);
    interactor.setInteractorStyle(interact_style);

    // Orientation marker

    const axes = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
    axes.setXPlusFaceProperty({text: '+X'});
    axes.setXMinusFaceProperty({text: '-X'});
    axes.setYPlusFaceProperty({text: '+Y'});
    axes.setYMinusFaceProperty({text: '-Y'});
    axes.setZPlusFaceProperty({text: '+Z'});
    axes.setZMinusFaceProperty({text: '-Z'});

    const orientationWidget = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
        actor: axes,
        interactor: interactor });
    orientationWidget.setEnabled(true);
    orientationWidget.setViewportCorner(vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.BOTTOM_LEFT);
    orientationWidget.setViewportSize(0.2);

};


new Promise(
  function(resolve, reject)
  {
    if (typeof(require) !== "undefined" ){
        require.config({
         "paths": {"vtk": "https://unpkg.com/vtk"},
        });
        require(["vtk"], resolve, reject);
    } else if ( typeof(vtk) === "undefined" ){
        var script = document.createElement("script");
    	script.onload = resolve;
    	script.onerror = reject;
    	script.src = "https://unpkg.com/vtk.js";
    	document.head.appendChild(script);
    } else { resolve() };
 }
).then(() => {
    // data, div_id and ratio are templated by python
    const div_id = "$div_id";
    const data = $data;
    const ratio = $ratio;

    render(data, div_id, ratio);
});
