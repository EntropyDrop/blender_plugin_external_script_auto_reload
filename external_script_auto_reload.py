import bpy
import traceback
import os

bl_info = {
    "name": "External Script Auto Reload",
    "author": "",
    "description": "real-time external text file update into Blender Text Editor and execute when file changes",
    "blender": (2, 81, 0),
    "location": "Properties > Scene > External Script",
    "warning": "",
    "category": "Text Editor"
}

poll_timer = None

def execute_external_script(context, filepath):
    try:
        with open(filepath, 'r') as file:
            script_code = file.read()
        
        global_dict = {
            'bpy': bpy,
            'context': context,
            'C': context,
            'D': bpy.data
        }
        
        exec(script_code, global_dict)
        print(f"exec: {filepath}")
    except Exception as e:
        print(f"err: {e}")
        error_traceback = traceback.format_exc()

def modify_internal_text():
    scene = bpy.context.scene
    if not hasattr(scene, 'external_script'):
        return
        
    path = scene.external_script
    if not path or not os.path.exists(path):
        return
        
    name = os.path.split(path)[-1]
    text = bpy.data.texts.get(name)
    if not text:
        text = bpy.data.texts.new(name)
    with open(path, 'r') as file:
        text.from_string(file.read())

def poll_text():
    scene = bpy.context.scene
    if not hasattr(scene, 'external_script'):
        return 1.0
        
    external_script = scene.external_script
    if external_script and os.path.exists(external_script):
        mtime = os.path.getmtime(external_script)
        if not hasattr(poll_text, 'mtime_prev') or mtime != poll_text.mtime_prev:
            modify_internal_text()
            
            if hasattr(scene, 'external_script_auto_execute') and scene.external_script_auto_execute:
                execute_external_script(bpy.context, external_script)
                
            poll_text.mtime_prev = mtime
    return 1.0

class SCENE_PT_external_script_panel(bpy.types.Panel):
    bl_label = "External script"
    bl_idname = "SCENE_PT_external_script_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, "external_script")
        layout.prop(scene, "external_script_auto_execute")
        layout.operator("scene.reload_external_script")

class SCENE_OT_reload_external_script(bpy.types.Operator):
    bl_idname = "scene.reload_external_script"
    bl_label = "reload"
    
    def execute(self, context):
        scene = context.scene
        modify_internal_text()
        
        if hasattr(scene, 'external_script_auto_execute') and scene.external_script_auto_execute:
            execute_external_script(context, scene.external_script)
            
        return {'FINISHED'}

def register():
    global poll_timer
    
    bpy.utils.register_class(SCENE_PT_external_script_panel)
    bpy.utils.register_class(SCENE_OT_reload_external_script)
    
    bpy.types.Scene.external_script = bpy.props.StringProperty(
        name="External Script",
        description="",
        subtype='FILE_PATH',
        default=""
    )
    
    bpy.types.Scene.external_script_auto_execute = bpy.props.BoolProperty(
        name="autorun",
        description="",
        default=False
    )
    
    if not hasattr(poll_text, 'mtime_prev'):
        poll_text.mtime_prev = -1
    
    poll_timer = bpy.app.timers.register(poll_text)

def unregister():
    global poll_timer
    
    if poll_timer:
        bpy.app.timers.unregister(poll_timer)
    
    if hasattr(bpy.types.Scene, 'external_script'):
        del bpy.types.Scene.external_script
        
    if hasattr(bpy.types.Scene, 'external_script_auto_execute'):
        del bpy.types.Scene.external_script_auto_execute
    
    bpy.utils.unregister_class(SCENE_OT_reload_external_script)
    bpy.utils.unregister_class(SCENE_PT_external_script_panel)

if __name__ == "__main__":
    register()