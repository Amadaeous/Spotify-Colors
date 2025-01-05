import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

# Specify the file path
file_path = 'colors.bin'

# Load the .bin file
data = np.fromfile(file_path, dtype=np.float32)

# Reshape the data to the desired dimensions
data = data.reshape((200, 3))

# Initialize the MinMaxScaler
scaler = MinMaxScaler()

# Fit and transform the data
scaled_data = scaler.fit_transform(data)

# Multiply each value by 255
scaled_data = scaled_data * 255

# Convert to integer type for RGB values
rgb_data = scaled_data.astype(np.uint8)

# Create a grid visualization of the RGB values
fig, ax = plt.subplots(figsize=(10, 2))

# Create an image grid with the RGB values
image_grid = np.reshape(rgb_data, (1, 200, 3))

# Display the image grid
ax.imshow(image_grid, aspect='auto')

# Remove axes for clarity
ax.axis('on')

# Set title
plt.title('RGB Color Grid')

plt.show()
