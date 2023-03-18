import numpy

def draw_line(matrix, x1, y1, x2, y2):
    # determine if line is steep
    is_steep = abs(y2 - y1) > abs(x2 - x1)

    # if line is steep, transpose the matrix
    if is_steep:
        matrix = [[matrix[j][i] for j in range(len(matrix))] for i in range(len(matrix[0]))]
        x1, y1 = y1, x1
        x2, y2 = y2, x2

    # swap the endpoints if necessary so that we're always drawing left to right
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1

    # calculate the slope of the line and the y-intercept
    dx = x2 - x1
    dy = abs(y2 - y1)
    slope = dy / dx if dx != 0 else 0
    y_intercept = y1 - slope * x1

    # draw the line, applying inverse text markup to the characters in the matrix
    x = x1
    y = y1
    while x <= x2:
        if 0 <= x < len(matrix[0]) and 0 <= y < len(matrix):
            matrix[y][x] = "█" * len(matrix[y][x])
        y = int(round(slope * x + y_intercept))
        x += 1

    # if line was steep, transpose the matrix back to its original orientation
    if is_steep:
        matrix = [[matrix[j][i] for j in range(len(matrix))] for i in range(len(matrix[0]))]

    return matrix

def calculate_end_coordinates(start_x, start_y, angle, length):
    # Convert the angle from degrees to radians
    angle_in_radians = numpy.radians(angle)
    
    # Calculate the change in x and y based on the angle and length
    delta_x = length * numpy.cos(angle_in_radians)
    delta_y = length * numpy.sin(angle_in_radians)
    
    # Calculate the end x and y coordinates
    end_x = start_x + delta_x
    end_y = start_y + delta_y
    
    return end_x, end_y

# takes in a string and outputs a list matrix
def string2matrix(string, item_size):
  list_matrix = string.split('\n')

  new_matrix = []
  for row in list_matrix:
    new_row = []

    item = ''
    for character_index in range(len(row)):
      if len(item) < item_size:
        item += row[character_index]
        
      if len(item) >= item_size:
        new_row.append(item)
        item = ''

    # append any aditional items that did not meet the size constrainst
    new_row.append(item)
      
    new_matrix.append(new_row)

  return new_matrix
  
