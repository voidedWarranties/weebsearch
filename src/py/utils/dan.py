# set up deepdanbooru and tensorflow
# logs should be disabled in env before importing this
from deepdanbooru.project import load_model_from_project, load_tags_from_project
from deepdanbooru.commands import evaluate_image
import numpy as np

def setup_dan(project_dir):
    import tensorflow as tf

    # set gpu config for rtx
    gpus = tf.config.list_physical_devices("GPU")
    try:
        tf.config.experimental.set_memory_growth(gpus[0], True)
    except (ValueError, RuntimeError) as e:
        pass

    model = load_model_from_project(project_dir)
    tags = load_tags_from_project(project_dir)
    def evaluate(path_or_bytes):
        tags_out = evaluate_image(path_or_bytes, model, tags, 0.5)
        tags_out = np.array(list(tags_out), dtype="str").tolist()

        rating = tags_out.pop(-1)
        tags_out.sort(key=lambda x: x[1], reverse=True)
        return tags_out, rating
    
    return evaluate