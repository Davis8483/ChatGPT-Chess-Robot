import numpy

# draw a line on a pixel matrix, (0, 0) is in the upper right corner 
def draw_line(matrix, x1, y1, x2, y2, char):
    # swap the endpoints if necessary so that we're always drawing right to left
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1

    # translate coordinates to the upper right corner
    x1 = len(matrix[0]) - x1 + 1
    x2 = len(matrix[0]) - x2 + 1

    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = -1 if x1 > x2 else 1
    sy = -1 if y1 > y2 else 1
    err = dx - dy

    while x1 != x2 or y1 != y2:
        # draw the pixel at (x1, y1)
        if 0 <= x1 < len(matrix[0]) and 0 <= y1 < len(matrix):
            matrix[y1][x1] = char * len(matrix[y1][x1])

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy

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
    
    return round(end_x), round(end_y)

# takes in a string and outputs a list matrix
def string2matrix(string, item_size):
    # Split the string into rows, and remove any empty rows
    rows = [row for row in string.split('\n') if row.strip()]

    # Split each row into items of the specified size
    matrix = [[row[i:i+item_size] for i in range(0, len(row), item_size)] for row in rows]

    return matrix

def matrix2string(matrix):
   
    output = ''

    for row in matrix:
        for item in row:
            output += item
        output += '\n'

    return output