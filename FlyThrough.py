#Author-Brian Ekins
#Description-Let user pick points or sketch curves for the camera to use for eye and target points.

import adsk.core, adsk.fusion, traceback
import math

_app = None
_ui = None
_handlers = []
_isValid = False
_inputs = None
_doAnimation = False

# Create all of the needed command inputs.
class flyCommandCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__() 
    def notify(self, args):
        try:
            cmd = adsk.core.Command.cast(args.command)
            inputs = cmd.commandInputs
            
            # Add drop-down for the type of animation.
            animationType = adsk.core.DropDownCommandInput.cast(inputs.addDropDownCommandInput('animType', 'Type', adsk.core.DropDownStyles.LabeledIconDropDownStyle))
            animationType.listItems.add('Fly along path', True, 'Resources/FlyAlong')
            animationType.listItems.add('Eye and Target paths', False, 'Resources/EyeAndTarget')

            # Add selection for the path curve.
            pathSelInput = adsk.core.SelectionCommandInput.cast(inputs.addSelectionInput('pathCurve', 'Path curve', 'Select the path curve.'))
            pathSelInput.setSelectionLimits(1,1)
            pathSelInput.addSelectionFilter('SketchCurves')
            pathSelInput.addSelectionFilter('Edges')
            
            # Add selection for the eye curve or point.
            eyeSelInput = adsk.core.SelectionCommandInput.cast(inputs.addSelectionInput('eyeCurve', 'Eye curve', 'Select the eye curve or point.'))
            eyeSelInput.setSelectionLimits(1,1)
            eyeSelInput.addSelectionFilter('Vertices')
            eyeSelInput.addSelectionFilter('SketchCurves')
            eyeSelInput.addSelectionFilter('SketchPoints')
            eyeSelInput.addSelectionFilter('ConstructionPoints')
            eyeSelInput.addSelectionFilter('Edges')
            eyeSelInput.isVisible = False
 
            # Add selection for the target curve or point.
            targetSelInput = inputs.addSelectionInput('targetCurve', 'Target curve', 'Select the target curve or point.')
            targetSelInput.setSelectionLimits(1,1)
            targetSelInput.addSelectionFilter('Vertices')
            targetSelInput.addSelectionFilter('SketchCurves')
            targetSelInput.addSelectionFilter('SketchPoints')
            targetSelInput.addSelectionFilter('ConstructionPoints')
            targetSelInput.addSelectionFilter('Edges')
            targetSelInput.isVisible = False

            # Add an input to specify the up direction.
            upDirInput = inputs.addDropDownCommandInput('upDir', 'Up Direction', adsk.core.DropDownStyles.LabeledIconDropDownStyle)
            listItems = upDirInput.listItems
            listItems.add('+X', False)
            listItems.add('-X', False)
            listItems.add('+Y', False)
            listItems.add('-Y', False)
            listItems.add('+Z', True)
            listItems.add('-Z', False)

            # Add slider for smoothness.
            rangeFloat = inputs.addFloatSliderCommandInput('smoothness', 'Quality', 'cm', 1, 100, False)
            rangeFloat.setText('Fast', 'Smooth')
            
            # Add check box for banking when using a single curve.
            bankCameraInput = inputs.addBoolValueInput('bankCamera', 'Corner bank', True, '', False)
            bankCameraInput.isVisible = False

            # Add check box for hiding the sketch curve paths.
            hidePathsInput = inputs.addBoolValueInput('hidePaths', 'Hide Paths', True, '', True)

            # Add button to animate.
            boolInput = inputs.addBoolValueInput('animate', 'Animate', False, './/Resources//Animate', False)
            boolInput.isEnabled = False

            # Connect to command related events.            
            flyCommandInputChanged = flyCommandInputChangedHandler()
            cmd.inputChanged.add(flyCommandInputChanged)
            _handlers.append(flyCommandInputChanged) 
            
            flyCommandValidateInputs = flyCommandValidateInputsHandler()
            cmd.validateInputs.add(flyCommandValidateInputs)
            _handlers.append(flyCommandValidateInputs) 

            flyCommandExecute = flyCommandExecutedHandler()
            cmd.execute.add(flyCommandExecute)
            _handlers.append(flyCommandExecute)
            
            FlyCommandActivate = flyCommandActivateHandler()
            cmd.activate.add(FlyCommandActivate)
            _handlers.append(FlyCommandActivate)
            
            FlyCommandExecutePreview = flyCommandExecutePreviewHandler()
            cmd.executePreview.add(FlyCommandExecutePreview)
            _handlers.append(FlyCommandExecutePreview)
            
            cmd.okButtonText = 'Save settings and exit'
        except:
            if _ui:
                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))    


# Read the attributes and set up the dialog based on the previously saved settings.
class flyCommandActivateHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        eventArgs = adsk.core.CommandEventArgs.cast(args)
        inputs = eventArgs.firingEvent.sender.commandInputs
        
        des = adsk.fusion.Design.cast(_app.activeProduct)

        # Get all of the inputs.
        animTypeInput = adsk.core.DropDownCommandInput.cast(inputs.itemById('animType'))
        pathSelectInput = inputs.itemById('pathCurve')
        eyeSelectInput = inputs.itemById('eyeCurve')
        targetSelectInput = inputs.itemById('targetCurve')
        bankCurveBoolInput = inputs.itemById('bankCamera')
        smoothSliderInput = inputs.itemById('smoothness')
        upDirectionInput = inputs.itemById('upDir')
        hidePathsInput = inputs.itemById('hidePaths')

        # Get the settings from attributes on the Design.
        animTypeAttrib = des.attributes.itemByName('sampleCameraAnimate', 'animType')
        if animTypeAttrib:
            animType = animTypeAttrib.value
            if animType == 'Fly along path':
                animTypeInput.listItems.item(0).isSelected = True
                targetSelectInput.isVisible = False
                targetSelectInput.clearSelection()
                eyeSelectInput.isVisible = False
                eyeSelectInput.clearSelection()
                pathSelectInput.isVisible = True
                #bankCurveBoolInput.isVisible = True
            else:
                animTypeInput.listItems.item(1).isSelected = True
                targetSelectInput.isVisible = True
                eyeSelectInput.isVisible = True
                pathSelectInput.isVisible = False
                pathSelectInput.clearSelection()
                #bankCurveBoolInput.isVisible = False

        upDirAttrib = des.attributes.itemByName('sampleCameraAnimate', 'upDir')
        if upDirAttrib:                    
            for listItem in upDirectionInput.listItems:
                if listItem.name == upDirAttrib.value:
                    listItem.isSelected = True
                    break

        smoothAttrib = des.attributes.itemByName('sampleCameraAnimate', 'smoothness')
        if smoothAttrib:                 
            smoothSliderInput.valueOne = float(smoothAttrib.value)

        hidePathsAttrib = des.attributes.itemByName('sampleCameraAnimate', 'hidePaths')
        if hidePathsAttrib:
            if hidePathsAttrib.value == 'True':
                hidePathsInput.value = True
            else:
                hidePathsInput.value = False
            
        bankCurveAttrib = des.attributes.itemByName('sampleCameraAnimate', 'bankCamera')
        if bankCurveAttrib:
            if bankCurveAttrib.value == 'True':
                bankCurveBoolInput.value = True
            else:
                bankCurveBoolInput.value = False
            
        # Get the curves.        
        attribs = des.findAttributes('sampleCameraAnimate', '')
        for attrib in attribs:
            if animType == 'Fly along path':
                if attrib.name == 'pathCurve':
                    pathCurve= attrib.parent
                    if pathCurve:
                        pathSelectInput.isEnabled = True
                        pathSelectInput.addSelection(pathCurve)                        
            else:
                if attrib.name == 'eyeCurve':
                    eyeCurve = attrib.parent
                    if eyeCurve:
                        eyeSelectInput.isEnabled = True
                        eyeSelectInput.addSelection(eyeCurve)
                elif attrib.name == 'targetCurve':
                    targetCurve = attrib.parent
                    if targetCurve:
                        targetSelectInput.isEnabled = True
                        targetSelectInput.addSelection(targetCurve)
                    

class flyCommandValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            validateArgs = adsk.core.ValidateInputsEventArgs.cast(args)
            inputs = validateArgs.inputs

            # Check that two selections are satisfied.
            global _isValid
            animateButton = inputs.itemById('animate')
            if areInputsValid(inputs):
                animateButton.isEnabled = True
                _isValid = True
            else:
                animateButton.isEnabled = False
                _isValid = False                
        except:
            if _ui:
                _ui.messageBox('Input changed event failed:\n{}'.format(traceback.format_exc()))


def areInputsValid(inputs):
    animationTypeInput = adsk.core.DropDownCommandInput.cast(inputs.itemById('animType'))
    animType = animationTypeInput.selectedItem.name
    if animType == 'Fly along path':
        pathSel = adsk.core.SelectionCommandInput.cast(inputs.itemById('pathCurve'))
        if pathSel.selectionCount == 0:
            return False
    else:
        eyeSel = adsk.core.SelectionCommandInput.cast(inputs.itemById('eyeCurve'))
        if eyeSel.selectionCount == 0:
            return False

        targetSel = adsk.core.SelectionCommandInput.cast(inputs.itemById('targetCurve'))
        if targetSel.selectionCount == 0:
            return False
    
    return True


# Event handler for the executePreview event.
class flyCommandExecutePreviewHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        eventArgs = adsk.core.CommandEventArgs.cast(args)
        inputs = eventArgs.command.commandInputs

        if _doAnimation:
            global _doAnimation
            _doAnimation = False

            if inputs.itemById('animType').selectedItem.name == 'Fly along path':
                doPathAnimation(inputs)
            else:                    
                doEyeTargetAnimation(inputs)


class flyCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface
            inputChangedArgs = adsk.core.InputChangedEventArgs.cast(args)
            inputs = inputChangedArgs.inputs

            # Get the input that changed.
            input = args.input

            # Do the animation, if all of the input has been defined.
            if input.id == 'animate' and _isValid: 
                global _doAnimation
                _doAnimation = True
            elif input.id == 'animType':
                # Get the current animation type.
                animTypeInput = adsk.core.DropDownCommandInput.cast(input)
                pathSelect = inputs.itemById('pathCurve')
                eyeSelect = inputs.itemById('eyeCurve')
                targetSelect = inputs.itemById('targetCurve')
                bankCurveBool = inputs.itemById('bankCamera')
                if animTypeInput.selectedItem.name == 'Fly along path':
                    targetSelect.isVisible = False
                    targetSelect.clearSelection()
                    eyeSelect.isVisible = False
                    eyeSelect.clearSelection()
                    pathSelect.isVisible = True
                    #bankCurveBool.isVisible = True
                else:
                    targetSelect.isVisible = True
                    eyeSelect.isVisible = True
                    pathSelect.isVisible = False
                    pathSelect.clearSelection()
                    #bankCurveBool.isVisible = False
            
            global _isValid
            animateButton = inputs.itemById('animate')
            if areInputsValid(inputs):
                animateButton.isEnabled = True
                _isValid = True
            else:
                animateButton.isEnabled = False
                _isValid = False                                
        except:
            if ui:
                ui.messageBox('Input changed event failed:\n{}'.format(traceback.format_exc()))


class flyCommandExecutedHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface
    
            # Add attributes to save the eye and target curves and the settings.
            if _isValid:
                # Save all of the settings as attributes.
                inputs = args.firingEvent.sender.commandInputs
                #doPathAnimation(inputs)
                saveSettings(inputs)                
        except:
            if ui:
                ui.messageBox('command executed failed:\n{}'.format(traceback.format_exc()))


def curveAsEvalOrPoint(inputEntity):
    if inputEntity.objectType == adsk.fusion.BRepEdge.classType():
        return inputEntity.evaluator
    elif isinstance(inputEntity, adsk.fusion.SketchCurve):
        worldGeom = inputEntity.worldGeometry
        if type(worldGeom) is adsk.core.NurbsCurve3D:
            return worldGeom.evaluator
        else:
            return worldGeom.asNurbsCurve.evaluator
    elif inputEntity.objectType == adsk.fusion.SketchPoint.classType():
        return inputEntity.worldGeometry
    elif inputEntity.objectType == adsk.fusion.ConstructionPoint.classType():
        return inputEntity.geometry
    elif inputEntity.objectType == adsk.fusion.BRepVertex.classType():
        return inputEntity.geometry


# Add attributes to save the eye and target curves and the settings.
def saveSettings(inputs):
    try:
        # Get the settings.
        upDirInput = inputs.itemById('upDir')
        upDir = upDirInput.selectedItem.name
        
        smoothInput = inputs.itemById('smoothness')
        smoothness = smoothInput.valueOne
        
        bankInput = inputs.itemById('bankCamera')
        bank = bankInput.value
        
        hidePathsInput = inputs.itemById('hidePaths')
        hidePaths = hidePathsInput.value            
        
        animationType = adsk.core.DropDownCommandInput.cast(inputs.itemById('animType'))
        animType = animationType.selectedItem.name

        # Add attributes to remember the entities and save the settings.
        if animType == 'Fly along path':
            pathInput = inputs.itemById('pathCurve')
            pathCurve = pathInput.selection(0).entity
        else:
            eyeInput = inputs.itemById('eyeCurve')
            eyeCurve = eyeInput.selection(0).entity

            targetInput = inputs.itemById('targetCurve')
            targetCurve = targetInput.selection(0).entity

        # Save geometry independent data on Design.
        des = adsk.fusion.Design.cast(_app.activeProduct)
        des.attributes.add('sampleCameraAnimate', 'animType', animType)
        des.attributes.add('sampleCameraAnimate', 'upDir', upDir)
        des.attributes.add('sampleCameraAnimate', 'smoothness', str(smoothness))
        des.attributes.add('sampleCameraAnimate', 'hidePaths', str(hidePaths))
        des.attributes.add('sampleCameraAniamte', 'bankCamera', str(bank))

        if animType == 'Fly along path':
            addSingleName(des, pathCurve, 'sampleCameraAnimate', 'pathCurve')
        else:
            addSingleName(des, eyeCurve, 'sampleCameraAnimate', 'eyeCurve')
            addSingleName(des, targetCurve, 'sampleCameraAnimate', 'targetCurve')
    except:
        if _ui:
            _ui.messageBox('command executed failed:\n{}'.format(traceback.format_exc()))
            

# Function that adds an attribute to an entity if it doesn't already exist, and
# it removes any attributes with the same name from any other entities so that
# only one entity can have an attribute with this name at a time.            
def addSingleName(design, entity, groupName, attributeName):
    attrib = entity.attributes.itemByName(groupName, attributeName)
    if not attrib:
        # Get the existing attribute from the old path and delete it.
        oldAttribs = design.findAttributes(groupName, attributeName)
        for oldAttrib in oldAttribs:
            oldAttrib.deleteMe()

        entity.attributes.add(groupName, attributeName, '')


def doPathAnimation(inputs):
    try:
        view = _app.activeViewport

        # Get the values from the command inputs.
        smoothInput = inputs.itemById('smoothness')
        smoothness = smoothInput.valueOne
        numPoints = int(smoothness * 20)
        
        bankedInput = inputs.itemById('bankCamera')
        isBanked = bankedInput.value
            
        pathInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('pathCurve'))
        pathCurve = pathInput.selection(0).entity
        pathEval = adsk.core.CurveEvaluator3D.cast(curveAsEvalOrPoint(pathCurve))

        hidePathsInput = inputs.itemById('hidePaths')
        hidePaths = hidePathsInput.value
        sketchIsVisible = False
        if hidePaths:
            # Check to see if the path curve is a sketch curve.
            if isinstance(pathCurve, adsk.fusion.SketchEntity):
                pathInput.clearSelection()

                skEnt = adsk.fusion.SketchEntity.cast(pathCurve)
                parentSketch = skEnt.parentSketch
                if parentSketch.isVisible:
                    sketchIsVisible = True
                    parentSketch.isVisible = False
                else:
                    sketchIsVisible = False

        upDirInput = inputs.itemById('upDir')
        upDir = upDirInput.selectedItem.name
        if upDir == "+X":
            upDirection = adsk.core.Vector3D.create(1.0, 0.0, 0.0)
        elif upDir == "-X":
            upDirection = adsk.core.Vector3D.create(-1.0, 0.0, 0.0)
        elif upDir == "+Y":
            upDirection = adsk.core.Vector3D.create(0.0, 1.0, 0.0)
        elif upDir == "-Y":
            upDirection = adsk.core.Vector3D.create(0.0, -1.0, 0.0)
        elif upDir == "+Z":
            upDirection = adsk.core.Vector3D.create(0.0, 0.0, 1.0)
        elif upDir == "-Z":
            upDirection = adsk.core.Vector3D.create(0.0, 0.0, -1.0)

        (retVal, pathMin, pathMax) = pathEval.getParameterExtents()
        (retVal, pathLength) = pathEval.getLengthAtParameter(pathMin, pathMax)
        eyeTargetOffset = pathLength * .0001
          
        for step in range(0, numPoints):
            currentEyeLength = (pathLength * (step/numPoints)) - eyeTargetOffset  
            (retVal, currentEyeParam) = pathEval.getParameterAtLength(pathMin, currentEyeLength)
            (retVal, currentEyePoint) = pathEval.getPointAtParameter(currentEyeParam)

            currentTargetLength = pathLength * (step/numPoints)  
            (retVal, currentTargetParam) = pathEval.getParameterAtLength(pathMin, currentTargetLength)
            (retVal, currentTargetPoint) = pathEval.getPointAtParameter(currentTargetParam)
            
            cam = view.camera
            cam.isSmoothTransition = False                
                
            cam.eye = currentEyePoint
            cam.target = currentTargetPoint
            
            if isBanked:
#                (retVal, curvatureDirection, curvature) = pathEval.getCurvature(currentEyeParam)
#                curvatureDirection.scaleBy(10)
#                influence = math.sin(upDirection.angleTo(curvatureDirection))
#                influence = influence * (1/curvature)
#                forwardDirection = currentEyePoint.vectorTo(currentTargetPoint)
#                sideDirection = upDirection.crossProduct(forwardDirection)
#                sideDirection.normalize()
#                sideDirection.scaleBy(influence)
#                newUpDirection = upDirection.copy()
#                newUpDirection.add(sideDirection)
#                cam.upVector = newUpDirection
                cam.upVector = upDirection
            else:
                cam.upVector = upDirection
            
            view.camera = cam
            view.refresh()
            adsk.doEvents()
            
        if hidePaths and sketchIsVisible:
            parentSketch.isVisible = True
            pathInput.isEnabled = True
            pathInput.addSelection(pathCurve)
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
  

def doEyeTargetAnimation(inputs):
    try:
        view = _app.activeViewport

        # Get the values from the command inputs.
        smoothInput = inputs.itemById('smoothness')
        smoothness = smoothInput.valueOne
        numPoints = int(smoothness * 20)
    
        eyeInput = adsk.core.SelectionCommandInput.cast(inputs.itemById('eyeCurve'))
        eyeCurve = eyeInput.selection(0).entity
        eyeEvalOrPoint = curveAsEvalOrPoint(eyeCurve)

        targetInput = inputs.itemById('targetCurve')                
        targetCurve = targetInput.selection(0).entity
        targetEvalOrPoint= curveAsEvalOrPoint(targetCurve)
        
        hidePathsInput = inputs.itemById('hidePaths')
        hidePaths = hidePathsInput.value
        eyeSketchIsVisible = False
        targetSketchIsVisible = False
        if hidePaths:
            # Check to see if the path curve is a sketch curve.
            if isinstance(eyeCurve, adsk.fusion.SketchEntity):
                eyeInput.clearSelection()
                skEnt = adsk.fusion.SketchEntity.cast(eyeCurve)
                eyeSketch = skEnt.parentSketch
                if eyeSketch.isVisible:
                    eyeSketchIsVisible = True
                    eyeSketch.isVisible = False
                else:
                    eyeSketchIsVisible = False

            if isinstance(targetCurve, adsk.fusion.SketchEntity):
                targetInput.clearSelection()
                skCurve = adsk.fusion.SketchCurve.cast(targetCurve)
                targetSketch = skCurve.parentSketch
                if targetSketch.isVisible:
                    targetSketchIsVisible = True
                    targetSketch.isVisible = False
                else:
                    targetSketchIsVisible = False

        upDirInput = inputs.itemById('upDir')
        upDir = upDirInput.selectedItem.name
        if upDir == "+X":
            upDirection = adsk.core.Vector3D.create(1.0, 0.0, 0.0)
        elif upDir == "-X":
            upDirection = adsk.core.Vector3D.create(-1.0, 0.0, 0.0)
        elif upDir == "+Y":
            upDirection = adsk.core.Vector3D.create(0.0, 1.0, 0.0)
        elif upDir == "-Y":
            upDirection = adsk.core.Vector3D.create(0.0, -1.0, 0.0)
        elif upDir == "+Z":
            upDirection = adsk.core.Vector3D.create(0.0, 0.0, 1.0)
        elif upDir == "-Z":
            upDirection = adsk.core.Vector3D.create(0.0, 0.0, -1.0)

        eyeIsPoint = True
        if type(eyeEvalOrPoint) is adsk.core.CurveEvaluator3D:
            eyeIsPoint = False
            (retVal, eyeMin, eyeMax) = eyeEvalOrPoint.getParameterExtents() 
            (retVal, eyeLength) = eyeEvalOrPoint.getLengthAtParameter(eyeMin, eyeMax)    

        targetIsPoint = True
        if type(targetEvalOrPoint) is adsk.core.CurveEvaluator3D:
            targetIsPoint = False
            (retVal, targetMin, targetMax) = targetEvalOrPoint.getParameterExtents() 
            (retVal, targetLength) = targetEvalOrPoint.getLengthAtParameter(targetMin, targetMax)    
           
        for step in range(0, numPoints):
            if eyeIsPoint:
                currentEyePoint = eyeEvalOrPoint
            else:
                currentEyeLength = eyeLength * (step/numPoints)    
                (retVal, currentEyeParam) = eyeEvalOrPoint.getParameterAtLength(eyeMin, currentEyeLength)
                (retVal, currentEyePoint) = eyeEvalOrPoint.getPointAtParameter(currentEyeParam)

            if targetIsPoint:
                currentTargetPoint = targetEvalOrPoint
            else:
                currentTargetLength = targetLength * (step/numPoints)            
                (retVal, currentTargetParam) = targetEvalOrPoint.getParameterAtLength(targetMin, currentTargetLength)
                (retVal, currentTargetPoint) = targetEvalOrPoint.getPointAtParameter(currentTargetParam)
            
            cam = view.camera
            cam.isSmoothTransition = False                
                
            cam.eye = currentEyePoint
            cam.target = currentTargetPoint
            cam.upVector = upDirection
            
            view.camera = cam
            view.refresh()
            adsk.doEvents() 
            
        if hidePaths:
            if eyeSketchIsVisible:
                eyeSketch.isVisible = True
                eyeInput.isEnabled = True
                eyeInput.addSelection(eyeCurve)            
            if targetSketchIsVisible:
                targetSketch.isVisible = True
                targetInput.isEnabled = True
                targetInput.addSelection(targetCurve)            
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
            
        
def run(context):
    try:
        global _app, _ui
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        # Get the CommandDefinitions collection.
        cmdDefs = _ui.commandDefinitions
        
        # Create a button command definition.
        flyCommandDef = cmdDefs.addButtonDefinition('sampleFlyThrough', 'Fly Through', 
                                                    'Fly camera along specified path',
                                                    './Resources/Fly' )
        flyCommandDef.toolClipFilename = './Resources/Fly/ToolClip.png'
        
        # Connect to the command related events.
        flyCommandCreated = flyCommandCreatedEventHandler()
        flyCommandDef.commandCreated.add(flyCommandCreated)
        _handlers.append(flyCommandCreated)

        # Get the NavBar toolbar. 
        navBar = _ui.toolbars.itemById('NavToolbar')
        
        # Add the button next to the fit command.
        flyButton = navBar.controls.addCommand(flyCommandDef, 'FitCommand', False)

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    try:
        cmdDefs = _ui.commandDefinitions

        flyCmd = cmdDefs.itemById('sampleFlyThrough')
        if flyCmd:
            flyCmd.deleteMe()
            
        navBar = _ui.toolbars.itemById('NavToolbar')
        cntrl = navBar.controls.itemById('sampleFlyThrough')
        if cntrl:
            cntrl.deleteMe()
        
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
