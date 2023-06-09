from pytorch3d.io import load_objs_as_meshes
import torch
import pyvista as pv
import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
from pathlib import Path

from pytorch3d.structures import Meshes
from pytorch3d.transforms import Transform3d
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
    TexturesVertex,
)
from semantic_mesh_pytorch3d.cameras import MetashapeCameraSet


class Pytorch3DMesh:
    def __init__(self, mesh_filename, camera_filename, image_folder, scale_factor=0.1):
        self.mesh_filename = mesh_filename
        self.scale_factor = scale_factor
        self.image_folder = image_folder

        self.pyvista_mesh = None
        self.pyvista_mesh = None
        # self.test_render()

        self.device = None
        if torch.cuda.is_available():
            self.device = torch.device("cuda:0")
            torch.cuda.set_device(self.device)
        else:
            self.device = torch.device("cpu")

        self.camera_set = MetashapeCameraSet(camera_filename)
        self.camera_set.rescale(self.scale_factor)
        self.load_mesh()

    def test_render(self):
        # mesh points
        vertices = np.array(
            [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0.5, 0.5, -1]]
        )

        # mesh faces
        faces = np.hstack(
            [
                [4, 0, 1, 2, 3],  # square
                [3, 0, 1, 4],  # triangle
                [3, 1, 2, 4],  # triangle
            ]
        )

        surf = pv.PolyData(vertices, faces)
        pv.start_xvfb()
        # plot each face with a different color
        surf.plot(
            scalars=np.arange(3),
            cpos=[-1, 1, 0.5],
            show_scalar_bar=False,
            show_edges=True,
            line_width=5,
            off_screen=True,
        )

    def load_example_mesh(self):
        self.pytorch_mesh = load_objs_as_meshes(
            ["data/cow_mesh/cow.obj"], device=self.device
        )

    def load_mesh(
        self,
        device=None,
        target_number=1000000,
        reload=False,
        reduction_frac=0.5,
        brightness_multiplier=8.0,
        standardize=True,
    ):
        if not reload:
            print("about to load")
            pyvista_mesh = pv.read(self.mesh_filename)

            while pyvista_mesh.points.shape[0] > target_number:
                pyvista_mesh = pyvista_mesh.decimate(target_reduction=0.5)
                print(f"number of points is {pyvista_mesh.points.shape[0]}")

            if standardize:
                mean = np.expand_dims(np.mean(pyvista_mesh.points, axis=0), axis=0)
                std = np.expand_dims(np.std(pyvista_mesh.points, axis=0), axis=0)
                new_points = pyvista_mesh.points * self.scale_factor
                pyvista_mesh.points = new_points
            self.pyvista_mesh = pyvista_mesh
            self.pyvista_mesh.save("data/decimated.ply")
        else:
            self.pyvista_mesh = pv.read("data/decimated.ply")
            print("loaded mesh")

        if brightness_multiplier != 1:
            self.pyvista_mesh["RGB"] = (
                self.pyvista_mesh["RGB"] * brightness_multiplier
            ).astype(np.uint8)
        verts = self.pyvista_mesh.points
        # See here for format: https://github.com/pyvista/pyvista-support/issues/96
        faces = self.pyvista_mesh.faces.reshape((-1, 4))[:, 1:4]

        verts = torch.Tensor(verts.copy()).to(self.device)
        faces = torch.Tensor(faces.copy()).to(self.device)

        # White texture from here https://github.com/facebookresearch/pytorch3d/issues/51
        verts_rgb = torch.Tensor(np.expand_dims(pyvista_mesh["RGB"] / 255, axis=0)).to(
            self.device
        )  # (1, V, 3)
        textures = TexturesVertex(verts_features=verts_rgb.to(device))

        self.pytorch_mesh = Meshes(verts=[verts], faces=[faces], textures=textures)

    def vis_pv(self):
        plotter = pv.Plotter(off_screen=False)
        self.camera_set.vis(plotter)
        plotter.add_mesh(self.pyvista_mesh, rgb=True)
        plotter.show(screenshot="vis/render.png")

    def render_geometric(self, n_cameras=200):
        # Initialize a camera.
        # With world coordinates +Y up, +X left and +Z in, the front of the cow is facing the -Z direction.
        # So we move the camera by 180 in the azimuth direction so it is facing the front of the cow.
        # TODO figure out what this should actually be
        inds = np.arange(len(self.camera_set.cameras))
        inds = inds[:1]
        # np.random.shuffle(inds)
        # if n_cameras is not None:
        #    inds = np.random.choice(inds, n_cameras)
        summed_values = ma.array(
            data=np.zeros((self.pyvista_mesh.points.shape[0], 3)),
            mask=np.ones((self.pyvista_mesh.points.shape[0], 3)).astype(bool),
        )
        counts = np.zeros((self.pyvista_mesh.points.shape[0], 3))
        num_complete = 0
        for i in inds:
            print(num_complete)
            num_complete += 1
            filename = self.camera_set.cameras[i].filename
            filepath = Path(self.image_folder, filename)
            img = plt.imread(filepath)
            plt.imshow(img)
            plt.show()
            colors_per_vertex = self.camera_set.cameras[i].splat_mesh_verts(
                self.pyvista_mesh.points, img
            )
            all_values = ma.stack((summed_values, colors_per_vertex), axis=2)
            summed_values = all_values.sum(axis=2)
            counts[np.logical_not(colors_per_vertex.mask)] = (
                counts[np.logical_not(colors_per_vertex.mask)] + 1
            )
        mean_colors = summed_values / counts
        plotter = pv.Plotter()
        plotter.add_mesh(self.pyvista_mesh, scalars=mean_colors / 50, rgb=True)
        plotter.show()

    def render(self):
        # Initialize a camera.
        # With world coordinates +Y up, +X left and +Z in, the front of the cow is facing the -Z direction.
        # So we move the camera by 180 in the azimuth direction so it is facing the front of the cow.
        # TODO figure out what this should actually be
        inds = np.arange(len(self.camera_set.cameras))
        np.random.shuffle(inds)
        for i in inds:
            filename = self.camera_set.cameras[i].filename
            filepath = Path(self.image_folder, filename)
            img = plt.imread(filepath)
            cameras = self.camera_set.cameras[i].get_pytorch3d_camera(self.device)

            # Define the settings for rasterization and shading. Here we set the output image to be of size
            # 512x512. As we are rendering images for visualization purposes only we will set faces_per_pixel=1
            # and blur_radius=0.0. We also set bin_size and max_faces_per_bin to None which ensure that
            # the faster coarse-to-fine rasterization method is used. Refer to rasterize_meshes.py for
            # explanations of these parameters. Refer to docs/notes/renderer.md for an explanation of
            # the difference between naive and coarse-to-fine rasterization.
            image_size = (img.shape[0], img.shape[1])
            raster_settings = RasterizationSettings(
                image_size=image_size, blur_radius=0.0, faces_per_pixel=1,
            )

            # Place a point light in front of the object. As mentioned above, the front of the cow is facing the
            # -z direction.
            lights = PointLights(device=self.device, location=[[0.0, 0.0, -3.0]])

            # Create a Phong renderer by composing a rasterizer and a shader. The textured Phong shader will
            # interpolate the texture uv coordinates for each vertex, sample from a texture image and
            # apply the Phong lighting model
            renderer = MeshRenderer(
                rasterizer=MeshRasterizer(
                    cameras=cameras, raster_settings=raster_settings
                ),
                shader=SoftPhongShader(
                    device=self.device, cameras=cameras, lights=lights
                ),
            )

            images = renderer(self.pytorch_mesh)
            f, ax = plt.subplots(1, 2)
            rendered = images[0, ..., :3].cpu().numpy()
            rendered = np.flip(rendered, (0, 1))
            ax[0].imshow(rendered)
            ax[1].imshow(img * 4)
            ax[0].set_title("Rendered image")
            ax[1].set_title("Real image")
            plt.axis("off")
            print(i)
            plt.savefig(f"vis/pred_{i:03d}.png")
            plt.close()
