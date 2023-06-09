from semantic_mesh_pytorch3d.meshes import Pytorch3DMesh
from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--mesh-file",
        default="/ofo-share/repos-david/Safeforest_CMU_data_dvc/data/site_Gascola/04_27_23/collect_05/processed_02/metashape/left_camera_automated/exports/example-run-001_20230517T1827_low_res_local.ply",
    )
    parser.add_argument(
        "--camera-file",
        default="/ofo-share/repos-david/Safeforest_CMU_data_dvc/data/site_Gascola/04_27_23/collect_05/processed_02/metashape/left_camera_automated/exports/example-run-001_20230517T1827_camera",
    )
    parser.add_argument(
        "--image-folder",
        default="/ofo-share/repos-david/Safeforest_CMU_data_dvc/data/site_Gascola/04_27_23/collect_05/processed_01/images/left_camera_0.5",
    )
    args = parser.parse_args()
    return args


def main(mesh_file, camera_file, image_folder):
    mesh = Pytorch3DMesh(mesh_file, camera_file, image_folder=image_folder)
    # mesh.vis_pv()
    mesh.render()
    mesh.render_geometric()


if __name__ == "__main__":
    args = parse_args()
    main(args.mesh_file, args.camera_file, args.image_folder)
