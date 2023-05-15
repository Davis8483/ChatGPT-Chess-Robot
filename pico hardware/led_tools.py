from pi_pico_neopixel.neopixel import Neopixel

class effects():
    
    def __init__(self, length: int):
        self.strip_length = length
        self.stats_pos = round(length / 2)
        self.stats_prev_index = 0
        self.pallet = {1: (255, 0, 0), 2: (0, 0, 0)}

    # rainbow accrost strip
    def rainbow(self, index: float, intensity: int):
        leds = []
        
        hue = round(65534 * index)

        for i in range(self.strip_length):

            color = Neopixel.colorHSV(Neopixel, hue, 255, 150)
            leds.append(color)
            
            if intensity != 0:
                hue += int(65534 * (intensity / 255) / 8)

        return leds

    # blinking effect between two colors
    # pallet 1 and 2
    def blink(self, index: float, intensity: int):
        leds = []
        
        for i in range(self.strip_length):
            if ((index * 100) % 20) < 10:
                leds.append(self.pallet[1])

            else:
                leds.append(self.pallet[2])

        return leds

    # creates a glowing effect between two colors
    # pallet 1 and 2
    def glow(self, index: float, intensity: int):
        leds = []
        
        # index is over the halway point, start changing back to the other color
        if index > 0.5:
            index = 0.5 - (index - 0.5)

        for i in range(self.strip_length):
            
            # cycle through each value in the color tuple
            color = []
            for v in range(3):
                
                value1 = round(self.pallet[1][v] * (index / 0.5))
                value2 = round(self.pallet[2][v] * ((0.5 - index) / 0.5))

                color.append(value1 + value2)

            leds.append(color)

        return leds
    

    def fade(self, index: float, intensity: int):
        leds = []

        for i in range(self.strip_length):
            
            color = []
            for v in range(3):
                
                value1 = round(self.pallet[1][v] * index)
                value2 = round(self.pallet[2][v] * (1 - index))

                color.append(value1 + value2)

            leds.append(color)

        return leds
    
    def chase(self, index: float, intensity: int):
        leds = []
        
        # make sure intensity is at least one so no math erors occur
        intensity += 1

        color_length = round(intensity / 16)

        color_id = 0 
        while (len(leds) < self.strip_length):

            color_id += 1
            if color_id > 2:
                color_id = 1

            for i in range(color_length):
                leds.append(self.pallet[color_id])

        # the strip should end with the opposite color so it loops back
        if color_id == 1:
            for i in range(color_length):
                leds.append(self.pallet[2])

        for i in range(round(index * len(leds))):
            first_led = leds[0]

            # remove the first
            leds.pop(0)

            # insert the first led last
            leds.append(first_led)
        
        return leds



    def gradient(self, index: float, intensity: int):
        leds = []
        
        ratio = intensity / 255.0
        color1_weight = 1 - ratio
        color2_weight = ratio
        
        for i in range(self.strip_length):
            # calculate the position of this LED as a fraction of the total length of the strip
            led_position = i / (self.strip_length - 1)
            
            # calculate the index for the gradient based on the position of this LED
            color_index = (index + led_position) % 1
            if color_index > 0.5:
                color_index = 1 - color_index
            
            # cycle through each value in the color tuple
            color = []
            for v in range(3):
                value1 = round(self.pallet[1][v] * color1_weight * (1 - color_index * 2))
                value2 = round(self.pallet[2][v] * color2_weight * (color_index * 2))

                color.append(value1 + value2)
            leds.append(color)
            
        return leds

    # used to display win/lose/draw stats of the chess game
    def stats(self, index: int, intensity: int):
        leds = []

        # add one to intensity so calculations don't break if 0
        intensity += 1
        
        # desired display bar position, also make sure at least 1 pixel of each color is showing
        target_pos = round((intensity / 255) * (self.strip_length - 2) + 1)

        for i in range(self.strip_length):
            
            # led has transitioned most of the way just make it full brightness
            if index < self.stats_prev_index:
                if self.stats_pos < target_pos:
                    self.stats_pos += 1

                elif self.stats_pos > target_pos:
                    self.stats_pos -= 1
                    
            # fade in the led to reach target position
            if (self.stats_pos < target_pos) and (i == self.stats_pos):

                color = []
                for v in range(3):
                    
                    value1 = round(self.pallet[1][v] * index)
                    value2 = round(self.pallet[2][v] * (1 - index))
                    
                    color.append(value1 + value2)
                
                leds.append(color)

            # fade out the led to reach target position
            elif (self.stats_pos > target_pos) and ((i + 1) == self.stats_pos):
                    
                color = []
                for v in range(3):
                    
                    value1 = round(self.pallet[1][v] * (1 - index))
                    value2 = round(self.pallet[2][v] * index)

                    color.append(value1 + value2)

                leds.append(color)
                
            elif i < self.stats_pos:
                leds.append(self.pallet[1])

            else:
                leds.append(self.pallet[2])

            self.stats_prev_index = index

        return leds


    fx_list = {
        "rainbow": rainbow, # rainbow waves
        "blink": blink, # flash between pallet colors 1 and 2
        "glow": glow, # transition between pallet colors 1 and 2
        "fade": fade, # fade pallet color 1 in while fading color 2 out
        "chase": chase, # two colors chasing after each other
        "gradient": gradient, # motion transition between colors 1 and 2
        "wld stats": stats # two colors with smooth transitions, used to display who is winning/losing
    }