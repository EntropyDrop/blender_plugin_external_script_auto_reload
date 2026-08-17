import os
import traceback

import bpy


bl_info = {
    "name": "External Script Auto Reload",
    "author": "",
    "description": "Reload and execute an external script when it changes",
    "blender": (2, 81, 0),
    "location": "Properties > Scene > External Script",
    "warning": "",
    "category": "Text Editor",
}


def _redraw_all_views(context):
    """Update evaluated data and redraw every open Blender area."""
    context.view_layer.update()
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def _normalize_dependencies(main_script, dependencies):
    """Resolve dependency paths relative to the main script."""
    script_dir = os.path.dirname(main_script)
    normalized = []
    for dependency in dependencies or ():
        dependency = os.fspath(dependency)
        if not os.path.isabs(dependency):
            dependency = os.path.join(script_dir, dependency)
        normalized.append(os.path.realpath(dependency))
    return tuple(dict.fromkeys(normalized))


def execute_external_script(context, filepath):
    """Execute a file with the globals expected by a normal Blender script."""
    filepath = os.path.realpath(filepath)
    try:
        with open(filepath, encoding="utf-8") as script_file:
            script_code = script_file.read()

        global_dict = {
            "__name__": "__main__",
            "__file__": filepath,
            "__package__": None,
            "BLENDER_EXTERNAL_SCRIPT_AUTO_RELOAD": True,
            "bpy": bpy,
            "context": context,
            "C": context,
            "D": bpy.data,
        }
        exec(compile(script_code, filepath, "exec"), global_dict)

        dependencies = _normalize_dependencies(
            filepath,
            global_dict.get("AUTO_RELOAD_DEPENDENCIES", ()),
        )
        _redraw_all_views(context)
        print(f"Executed: {filepath}")
        return dependencies
    except Exception:
        traceback.print_exc()
        _redraw_all_views(context)
        return None


def modify_internal_text():
    scene = bpy.context.scene
    if not hasattr(scene, "external_script"):
        return

    path = bpy.path.abspath(scene.external_script)
    if not path or not os.path.exists(path):
        return

    name = os.path.basename(path)
    text = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    with open(path, encoding="utf-8") as script_file:
        text.from_string(script_file.read())


def _watched_paths(main_script):
    dependencies = getattr(poll_text, "dependencies", ())
    return (os.path.realpath(main_script), *dependencies)


def _watch_signature(main_script):
    signature = []
    for path in _watched_paths(main_script):
        try:
            stat = os.stat(path)
            file_state = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            file_state = None
        signature.append((path, file_state))
    return tuple(signature)


def _execute_and_track(context, filepath):
    dependencies = execute_external_script(context, filepath)
    if dependencies is not None:
        poll_text.dependencies = dependencies


def poll_text():
    scene = bpy.context.scene
    if not hasattr(scene, "external_script"):
        return 1.0

    external_script = bpy.path.abspath(scene.external_script)
    if external_script and os.path.exists(external_script):
        signature = _watch_signature(external_script)
        if signature != getattr(poll_text, "signature_prev", None):
            modify_internal_text()
            if scene.external_script_auto_execute:
                _execute_and_track(bpy.context, external_script)
            poll_text.signature_prev = _watch_signature(external_script)
    return 1.0


class SCENE_PT_external_script_panel(bpy.types.Panel):
    bl_label = "External script"
    bl_idname = "SCENE_PT_external_script_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "external_script")
        layout.prop(scene, "external_script_auto_execute")
        layout.operator("scene.reload_external_script")


class SCENE_OT_reload_external_script(bpy.types.Operator):
    bl_idname = "scene.reload_external_script"
    bl_label = "Reload"

    def execute(self, context):
        scene = context.scene
        external_script = bpy.path.abspath(scene.external_script)
        modify_internal_text()
        if scene.external_script_auto_execute:
            _execute_and_track(context, external_script)
        poll_text.signature_prev = _watch_signature(external_script)
        return {"FINISHED"}


CLASSES = (
    SCENE_PT_external_script_panel,
    SCENE_OT_reload_external_script,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.external_script = bpy.props.StringProperty(
        name="External Script",
        subtype="FILE_PATH",
        default="",
    )
    bpy.types.Scene.external_script_auto_execute = bpy.props.BoolProperty(
        name="Autorun",
        default=False,
    )

    poll_text.signature_prev = None
    poll_text.dependencies = ()
    if not bpy.app.timers.is_registered(poll_text):
        bpy.app.timers.register(poll_text)


def unregister():
    if bpy.app.timers.is_registered(poll_text):
        bpy.app.timers.unregister(poll_text)

    if hasattr(bpy.types.Scene, "external_script"):
        del bpy.types.Scene.external_script
    if hasattr(bpy.types.Scene, "external_script_auto_execute"):
        del bpy.types.Scene.external_script_auto_execute

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
