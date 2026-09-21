"""
Train the waste classification CNN using transfer learning on MobileNetV2.

Usage:
    python ml/train_classifier.py --data_dir /path/to/dataset --epochs 15

Expected dataset layout (standard Keras ImageDataGenerator format):
    dataset/
        Plastic/*.jpg
        Paper/*.jpg
        Metal/*.jpg
        Glass/*.jpg
        Organic/*.jpg
        E-waste/*.jpg
        Other/*.jpg

A good starting public dataset is TrashNet (github.com/garythung/trashnet)
plus additional E-waste and "Other" images scraped/collected for this
project; merge/relabel folders into the 7 classes above before training.

This script:
  1. Loads MobileNetV2 pretrained on ImageNet, excluding the top layer.
  2. Freezes the base and trains a new dense classification head
     (GlobalAveragePooling -> Dense(256, relu) -> Dropout -> Dense(7, softmax)).
  3. Fine-tunes the last ~30 layers of the base at a low learning rate.
  4. Saves the trained model to ml/saved_models/waste_cnn.h5, which
     waste_classifier.py automatically picks up on the next classify request.
"""
import argparse
import os

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_PATH = os.path.join(MODEL_DIR, "waste_cnn.h5")
IMG_SIZE = (224, 224)
CLASSES = ["Plastic", "Paper", "Metal", "Glass", "Organic", "E-waste", "Other"]


def build_model(num_classes=len(CLASSES)):
    import tensorflow as tf
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras import layers, models

    base = MobileNetV2(input_shape=IMG_SIZE + (3,), include_top=False, weights="imagenet")
    base.trainable = False

    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))
    x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    model = models.Model(inputs, outputs)
    return model, base


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True, help="Path to dataset root (one folder per class)")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--fine_tune_epochs", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=32)
    args = parser.parse_args()

    import tensorflow as tf

    os.makedirs(MODEL_DIR, exist_ok=True)

    train_datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        validation_split=0.2, rotation_range=20, width_shift_range=0.1,
        height_shift_range=0.1, zoom_range=0.15, horizontal_flip=True,
    )

    train_gen = train_datagen.flow_from_directory(
        args.data_dir, target_size=IMG_SIZE, batch_size=args.batch_size,
        class_mode="categorical", subset="training", classes=CLASSES,
    )
    val_gen = train_datagen.flow_from_directory(
        args.data_dir, target_size=IMG_SIZE, batch_size=args.batch_size,
        class_mode="categorical", subset="validation", classes=CLASSES,
    )

    model, base = build_model()
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="categorical_crossentropy", metrics=["accuracy"])

    print("== Phase 1: training classification head (base frozen) ==")
    model.fit(train_gen, validation_data=val_gen, epochs=args.epochs)

    print("== Phase 2: fine-tuning top layers of MobileNetV2 ==")
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
                  loss="categorical_crossentropy", metrics=["accuracy"])
    model.fit(train_gen, validation_data=val_gen, epochs=args.fine_tune_epochs)

    model.save(MODEL_PATH)
    print(f"Saved trained model to {MODEL_PATH}")

    val_loss, val_acc = model.evaluate(val_gen)
    print(f"Final validation accuracy: {val_acc:.4f}")


if __name__ == "__main__":
    main()
