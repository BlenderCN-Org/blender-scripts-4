import bpy
from bpy.props import (IntProperty, 
                       FloatProperty, 
                       PointerProperty, 
                       CollectionProperty)
from .utils import MultiCamContext
from .multicam import MultiCam
    
class MultiCamFaderProperties(bpy.types.PropertyGroup):
    @classmethod
    def register(cls):
        bpy.types.Scene.multicam_fader_properties = CollectionProperty(type=cls)
        cls.start_source = IntProperty(name='Start Source')
        cls.next_source = IntProperty(name='Next Source')
        #cls.frame_duration = FloatProperty(name='Frame Duration', default=20.)
        cls.fade_position = FloatProperty(name='Fade Position', min=0., max=1.)
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.multicam_fader_properties
    @classmethod
    def get_for_data_path(cls, data_path, context=None):
        if context is None:
            context = bpy.context
        return context.scene.multicam_fader_properties.get(data_path)
    @classmethod
    def get_for_strip(cls, mc_strip, context=None):
        data_path = mc_strip.path_from_id()
        return cls.get_for_data_path(data_path, context)
    @classmethod
    def get_or_create(cls, **kwargs):
        context = kwargs.get('context')
        data_path = kwargs.get('data_path')
        if data_path is not None:
            prop = cls.get_for_data_path(data_path, context)
        else:
            mc_strip = kwargs.get('mc_strip')
            prop = cls.get_for_strip(mc_strip)
        created = prop is None
        if created:
            if data_path is None:
                data_path = mc_strip.path_from_id()
            prop = context.scene.multicam_fader_properties.add()
            prop.name = data_path
        return prop, created
    
class MultiCamFaderCreateProps(bpy.types.Operator, MultiCamContext):
    bl_idname = 'sequencer.multicam_create_props'
    bl_label = 'Multicam Fader Create Props'
    def execute(self, context):
        mc_strip = self.get_strip(context)
        MultiCamFaderProperties.get_or_create(context=context, mc_strip=mc_strip)
        return {'FINISHED'}
    
class DummyContext(object):
    def __init__(self, scene):
        self.scene = scene

class MultiCamFaderOpsProperties(bpy.types.PropertyGroup):
    def on_end_frame_update(self, context):
        start = self.get_start_frame(context)
        duration = self.end_frame - start
        if duration == self.frame_duration:
            return
        self.frame_duration = duration
    def on_frame_duration_update(self, context):
        start = self.get_start_frame(context)
        end = start + self.frame_duration
        if end == self.end_frame:
            return
        self.end_frame = end
    def get_start_frame(self, context=None):
        if context is None:
            context = bpy.context
        if isinstance(context, bpy.types.Scene):
            scene = context
        else:
            scene = context.scene
        return scene.frame_current_final
    @classmethod
    def register(cls):
        bpy.types.Scene.multicam_fader_ops_properties = PointerProperty(type=cls)
        cls.destination_source = IntProperty(
            name='Destination Source', 
            description='The source to transition to', 
        )
        cls.end_frame = FloatProperty(
            name='End Frame', 
            description='Ending frame for transition (relative to current)', 
            update=cls.on_end_frame_update, 
        )
        cls.frame_duration = FloatProperty(
            name='Frame Duration', 
            description='Duration of the transition', 
            default=20., 
            update=cls.on_frame_duration_update, 
        )
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.multicam_fader_ops_properties
    def update_props(self, context=None):
        if context is None:
            context = bpy.context
        self.on_frame_duration_update(context)
    @staticmethod
    def on_frame_change(scene):
        if bpy.context.screen.is_animation_playing:
            return
        prop = scene.multicam_fader_ops_properties
        prop.on_frame_duration_update(scene)
    
class MultiCamFader(bpy.types.Operator, MultiCamContext):
    bl_idname = 'scene.multicam_fader'
    bl_label = 'Multicam Fader'
    def get_start_frame(self, context=None):
        if context is None:
            context = bpy.context
        return context.scene.frame_current_final
    def execute(self, context):
        mc_strip = self.get_strip(context)
        fade_props, created = MultiCamFaderProperties.get_or_create(context=context, mc_strip=mc_strip)
        ops_props = context.scene.multicam_fader_ops_properties
        start_frame = self.get_start_frame(context)
        fade_props.start_source = mc_strip.multicam_source
        fade_props.next_source = ops_props.destination_source
        fade_props.fade_position = 0.
        data_path = fade_props.path_from_id()
        attrs = ['start_source', 'next_source', 'fade_position']
        for attr in attrs:
            context.scene.keyframe_insert(data_path='.'.join([data_path, attr]), 
                                          frame=start_frame, 
                                          group='Multicam Fader (%s)' % (mc_strip.name))
        fade_props.fade_position = 1.
        for attr in attrs:
            context.scene.keyframe_insert(data_path='.'.join([data_path, attr]), 
                                          frame=ops_props.end_frame, 
                                          group='Multicam Fader (%s)' % (mc_strip.name))
        multicam = MultiCam(blend_obj=mc_strip, context=context)
        multicam.insert_keyframe(start_frame, mc_strip.channel - 1, interpolation='CONSTANT')
        multicam.insert_keyframe(ops_props.end_frame, fade_props['next_source'], interpolation='CONSTANT')
        multicam.build_fade(fade=None, frame=start_frame)
        return {'FINISHED'}
        
    
def register():
    bpy.utils.register_class(MultiCamFaderProperties)
    bpy.utils.register_class(MultiCamFaderCreateProps)
    bpy.utils.register_class(MultiCamFaderOpsProperties)
    bpy.utils.register_class(MultiCamFader)
    bpy.app.handlers.frame_change_pre.append(MultiCamFaderOpsProperties.on_frame_change)
    
def unregister():
    bpy.utils.unregister_class(MultiCamFader)
    bpy.utils.unregister_class(MultiCamFaderOpsProperties)
    bpy.utils.unregister_class(MultiCamFaderCreateProps)
    bpy.utils.unregister_class(MultiCamFaderProperties)
