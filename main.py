import os, sys

import time
import argparse
import importlib
from tqdm import tqdm
from imageio import imread
import torch
import numpy as np
import matplotlib.pyplot as plt
import cv2
import random

import open3d as o3d
from plotly import graph_objs as go
# import plotly.graph_objects as go
from scipy.signal import correlate2d
from scipy.ndimage import shift
from skimage.transform import resize


from torchvision import transforms

from scipy.interpolate import RegularGridInterpolator

from flask import Flask, render_template, request
import os

from hashlib import sha1
from shutil import rmtree
from stat import S_ISREG, ST_CTIME, ST_MODE
import json
import os
import time

from PIL import Image, ImageFile
from gevent.event import AsyncResult
from gevent.queue import Empty, Queue
from gevent.timeout import Timeout
import flask
import numpy as np

import subprocess
# from flask_ngrok import run_with_ngrok

from pytorch3d.io import load_objs_as_meshes, load_obj

# Data structures and functions for rendering
from pytorch3d.structures import Meshes

from pytorch3d.renderer import (
    look_at_view_transform,
    FoVPerspectiveCameras, 
    PointLights, 
    DirectionalLights, 
    Materials, 
    RasterizationSettings, 
    MeshRenderer, 
    MeshRasterizer,  
    SoftPhongShader,
    TexturesUV,
    TexturesVertex
)

from pytorch3d.vis.plotly_vis import AxisArgs, plot_batch_individually, plot_scene
from pytorch3d.vis.texture_vis import texturesuv_image_matplotlib

import torch


DATA_DIR = 'data'
KEEP_ALIVE_DELAY = 25
MAX_IMAGE_SIZE = 512, 256
MAX_IMAGES = 1000
MAX_DURATION = 300

BROADCAST_QUEUE = Queue()
app = Flask(__name__)


# from flask_ngrok import run_with_ngrok
# run_with_ngrok(app)  # Start ngrok when app is run



# try:  # Reset saved files on each start
#     rmtree(DATA_DIR, True)
#     os.mkdir(DATA_DIR)
# except OSError:
#     pass


# def broadcast(message):
#     """Notify all waiting waiting gthreads of message."""
#     waiting = []
#     try:
#         while True:
#             waiting.append(BROADCAST_QUEUE.get(block=False))
#     except Empty:
#         pass
#     print('Broadcasting {} messages'.format(len(waiting)))
#     for item in waiting:
#         item.set(message)


# def receive():
#     """Generator that yields a message at least every KEEP_ALIVE_DELAY seconds.
#     yields messages sent by `broadcast`.
#     """
#     now = time.time()
#     end = now + MAX_DURATION
#     tmp = None
#     # Heroku doesn't notify when clients disconnect so we have to impose a
#     # maximum connection duration.
#     while now < end:
#         if not tmp:
#             tmp = AsyncResult()
#             BROADCAST_QUEUE.put(tmp)
#         try:
#             yield tmp.get(timeout=KEEP_ALIVE_DELAY)
#             tmp = None
#         except Timeout:
#             yield ''
#         now = time.time()


# def safe_addr(ip_addr):
#     """Strip off the trailing two octets of the IP address."""
#     return '.'.join(ip_addr.split('.')[:2] + ['xxx', 'xxx'])


# def save_normalized_image(path, data):
#     """Generate an RGB thumbnail of the provided image."""
#     image_parser = ImageFile.Parser()
#     try:
#         image_parser.feed(data)
#         image = image_parser.close()
#     except IOError:
#         return False
    
#     image_ori = image.copy()
#     image.save(os.path.join('/home/q10/ws/2021/metaverse/metaverse_/MAIN-Rebuilder/images_server', 'sample.jpg'))
#     image.thumbnail(MAX_IMAGE_SIZE, Image.ANTIALIAS)
#     if image.mode != 'RGB':
#         image = image.convert('RGB')
#     image.save(path)

#     # main(image_ori)
    

#     # subprocess.call('/home/q10/ws/repos/metaverse/MAIN-Rebuilder/infer.py', shell=True)
    
#     return True


# def event_stream(client):
#     """Yield messages as they come in."""
#     force_disconnect = False
#     try:
#         for message in receive():
#             yield 'data: {}\n\n'.format(message)
#         print('{} force closing stream'.format(client))
#         force_disconnect = True
#     finally:
#         if not force_disconnect:
#             print('{} disconnected from stream'.format(client))


# @app.route('/post', methods=['POST'])
# def post():
#     """Handle image uploads."""
#     sha1sum = sha1(flask.request.data).hexdigest()
#     target = os.path.join(DATA_DIR, '{}.png'.format(sha1sum))
#     message = json.dumps({'src': target,
#                           'ip_addr': safe_addr(flask.request.access_route[0])})
#     try:
#         if save_normalized_image(target, flask.request.data):
#             broadcast(message)  # Notify subscribers of completion
#     except Exception as exception:  # Output errors
#         return '{}'.format(exception)
#     return 'success'


# @app.route('/stream')
# def stream():
#     """Handle long-lived SSE streams."""
#     return flask.Response(event_stream(flask.request.access_route[0]),
#                           mimetype='text/event-stream')



# @app.route('/')
# def home():
#     """Provide the primary view along with its javascript."""
#     # Code adapted from: http://stackoverflow.com/questions/168409/
#     image_infos = []
#     for filename in os.listdir(DATA_DIR):
#         filepath = os.path.join(DATA_DIR, filename)
#         file_stat = os.stat(filepath)
#         if S_ISREG(file_stat[ST_MODE]):
#             image_infos.append((file_stat[ST_CTIME], filepath))

#     images = []
#     for i, (_, path) in enumerate(sorted(image_infos, reverse=True)):
#         if i >= MAX_IMAGES:
#             os.unlink(path)
#             continue
#         images.append('<div><img alt="User uploaded image" src="{}" /></div>'
#                       .format(path))
#     return """
# <!doctype html>
# <title>Image Uploader</title>
# <meta charset="utf-8" />
# <script src="//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js"></script>
# <script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.10.1/jquery-ui.min.js"></script>
# <link rel="stylesheet" href="//ajax.googleapis.com/ajax/libs/jqueryui/1.10.1/themes/vader/jquery-ui.css" />
# <style>
#   body {
#     max-width: 800px;
#     margin: auto;
#     padding: 1em;
#     background: black;
#     color: #fff;
#     font: 16px/1.6 menlo, monospace;
#     text-align:center;
#   }
#   a {
#     color: #fff;
#   }
#   .notice {
#     font-size: 80%%;
#   }
# #drop {
#     font-weight: bold;
#     text-align: center;
#     padding: 1em 0;
#     margin: 1em 0;
#     color: #555;
#     border: 2px dashed #555;
#     border-radius: 7px;
#     cursor: default;
# }
# #drop.hover {
#     color: #f00;
#     border-color: #f00;
#     border-style: solid;
#     box-shadow: inset 0 3px 4px #888;
# }
# </style>
# <h4>REBUILDER</h4>
# <h2>Upload your image, rebuild the world!</h2>
# <p>Upload and check :
# <a href="http://143.248.54.15:5501">this link!</a></p>
# <p class="notice">*this version is beta*</p>
# <noscript>*this version is beta*</noscript>
# <fieldset>
#   <p id="status">Select an image</p>
#   <div id="progressbar"></div>
#   <input id="file" type="file" />
#   <div id="drop">or drop image here</div>
# </fieldset>
# <h3>Uploaded Images (updated in real-time)</h3>
# <div id="images">%s</div>
# <script>
#   function sse() {
#       var source = new EventSource('/stream');
#       source.onmessage = function(e) {
#           if (e.data == '')
#               return;
#           var data = $.parseJSON(e.data);
#           var upload_message = 'Image uploaded by ' + data['ip_addr'];
#           var image = $('<img>', {alt: upload_message, src: data['src']});
#           var container = $('<div>').hide();
#           container.append($('<div>', {text: upload_message}));
#           container.append(image);
#           $('#images').prepend(container);
#           image.load(function(){
#               container.show('blind', {}, 1000);
#           });
#       };
#   }
#   function file_select_handler(to_upload) {
#       var progressbar = $('#progressbar');
#       var status = $('#status');
#       var xhr = new XMLHttpRequest();
#       xhr.upload.addEventListener('loadstart', function(e1){
#           status.text('uploading image');
#           progressbar.progressbar({max: e1.total});
#       });
#       xhr.upload.addEventListener('progress', function(e1){
#           if (progressbar.progressbar('option', 'max') == 0)
#               progressbar.progressbar('option', 'max', e1.total);
#           progressbar.progressbar('value', e1.loaded);
#       });
#       xhr.onreadystatechange = function(e1) {
#           if (this.readyState == 4)  {
#               if (this.status == 200)
#                   var text = 'upload complete: ' + this.responseText;
#               else
#                   var text = 'upload failed: code ' + this.status;
#               status.html(text + '<br/>Select an image');
#               progressbar.progressbar('destroy');
#           }
#       };
#       xhr.open('POST', '/post', true);
#       xhr.send(to_upload);
#   };
#   function handle_hover(e) {
#       e.originalEvent.stopPropagation();
#       e.originalEvent.preventDefault();
#       e.target.className = (e.type == 'dragleave' || e.type == 'drop') ? '' : 'hover';
#   }
#   $('#drop').bind('drop', function(e) {
#       handle_hover(e);
#       if (e.originalEvent.dataTransfer.files.length < 1) {
#           return;
#       }
#       file_select_handler(e.originalEvent.dataTransfer.files[0]);
#   }).bind('dragenter dragleave dragover', handle_hover);
#   $('#file').change(function(e){
#       file_select_handler(e.target.files[0]);
#       e.target.value = '';
#   });
#   sse();
#   var _gaq = _gaq || [];
#   _gaq.push(['_setAccount', 'UA-510348-17']);
#   _gaq.push(['_trackPageview']);
#   (function() {
#     var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
#     ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
#     var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
#   })();
# </script>
# """ % ('\n'.join(images))  # noqa








def obj_to_json(mesh: o3d.geometry.TriangleMesh):

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(instance_points[:, :3])
    mesh.vertex_colors = o3d.utility.Vector3dVector(instance_points[:,3:])
    mesh.triangles = o3d.utility.Vector3iVector(instance_faces)
    mesh.compute_vertex_normals()
    mesh.compute_adjacency_list()
    o3d.io.write_triangle_mesh("/home/q10/ws/2021/metaverse/metaverse_/Insert-3D-Objects-in-a-webpage-using-HTML-and-CSS-only/objects_3d/test.gltf", mesh)



    points = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.triangles)



    fig = go.Figure(
        data=[
            # go.Mesh3d(
            #     x=layout_points[:,0],
            #     y=-layout_points[:,1],
            #     z=layout_points[:,2],
            #     i=layout_faces[:,0],
            #     j=layout_faces[:,1],
            #     k=layout_faces[:,2],
            #     facecolor=layout_points[:,3:][layout_faces[:,0]]
            # ),
            go.Mesh3d(
                x=-instance_points[:,1],
                y=-instance_points[:,0],
                z=instance_points[:,2],
                i=instance_faces[:,0],
                j=instance_faces[:,1],
                k=instance_faces[:,2],
                facecolor=instance_points[:,3:][instance_faces[:,0]]
            ),
            # go.Scatter3d(
            #     x=instance_points_noface[:,1],
            #     y=-instance_points_noface[:,0],
            #     z=instance_points_noface[:,2], 
            #     mode='markers',
            #     marker=dict(size=2, color=instance_points_noface[:,3:]),
            # ),

        ],
        layout=dict(
            scene=dict(
                xaxis=dict(visible=True),
                yaxis=dict(visible=True),
                zaxis=dict(visible=True)
            )
        )
    )
    # fig.show()
    # fig.write_html("/home/q10/ws/repos/metaverse/MAIN-Rebuilder/index.html", full_html=True)

    with open("test_mesh.html", "w") as f:
        return fig.to_html(include_plotlyjs='cdn')



    pass



def main():

    # print("Testing IO for textured meshes ...")
    # mesh = o3d.io.read_triangle_mesh("sample/211206_lego/obj/mesh.obj")
    # print(mesh)


    # points = np.asarray(mesh.vertices)
    # faces = np.asarray(mesh.triangles)


    print("Testing IO for textured meshes ...")
    mesh = o3d.io.read_triangle_mesh("sample/211206_lego/obj/mesh.obj")
    print(mesh)

    points = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.triangles)
    uv_map = np.asarray(mesh.textures[1])
    triangle_uvs = np.asarray(mesh.triangle_uvs)

    textures = TexturesUV(maps=[torch.FloatTensor(np.asarray(mesh.textures[1])[..., :3])], \
    faces_uvs=torch.LongTensor(np.asarray(mesh.triangles)).unsqueeze(0), verts_uvs=torch.FloatTensor(mesh.triangle_uvs).unsqueeze(0))

    # Create a Meshes object
    mesh_viz = Meshes(
        verts=[torch.FloatTensor(points)],   
        faces=[torch.LongTensor(faces)],
        textures=textures
    )

    # Render the plotly figure
    fig = plot_scene({
        "subplot1": {
            "mesh": mesh_viz
        }
    })
    # fig.show()

    return fig.to_html(include_plotlyjs='cdn')




    pass



@app.route('/', methods=['GET', 'POST'])
def home():
    return main()





if __name__ == '__main__':
    # main()


    app.run(host='0.0.0.0', port=8080, debug=True)
    # app.run()




