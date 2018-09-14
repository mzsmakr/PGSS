import cv2
import os

def fort_image_matching(url_img_name, fort_img_name, crop_area = 0):
    url_img_basename = os.path.basename(url_img_name)
    url_img_basename, url_img_ext = os.path.splitext(url_img_basename)

    url_img = cv2.imread(url_img_name, 3)
    fort_img = cv2.imread(fort_img_name, 3)

    if url_img is None or fort_img is None:
        return 0.0

    height, width, channels = url_img.shape

    if url_img_ext == '.jpg':
        if width > height:
            scale = float(288 / height)
        else:
            scale = float(288 / width)

        height_f, width_f, channels_f = fort_img.shape

        scale_fort = width_f / 320

        url_img = cv2.resize(url_img, None, fx=scale * scale_fort, fy=scale * scale_fort,
                             interpolation=cv2.INTER_NEAREST)

        crop_y1 = 74
        crop_y2 = 246
        crop_x1 = 74
        crop_x2 = 144

        if crop_area == 1:
            crop_y1 = 74
            crop_y2 = 144
            crop_x1 = 134
            crop_x2 = 246

        crop = fort_img[int(crop_y1 * scale_fort):int(crop_y2 * scale_fort), int(crop_x1 * scale_fort):int(crop_x2 * scale_fort)]

        # Calculate vector from center of fort image(x=74, y=74, width=172, height=172) to top left corner of crop of fort_img
        fi_center_x = (((246 + 74) / 2) * scale_fort) - (crop_x1 * scale_fort)
        fi_center_y = (((246 + 74) / 2) * scale_fort) - (crop_y1 * scale_fort)

        if crop.mean() == 255 or crop.mean() == 0:
            return 0.0

        result = cv2.matchTemplate(url_img, crop, cv2.TM_CCOEFF_NORMED)
        min_val3, max_val3, min_loc3, max_loc3 = cv2.minMaxLoc(result)

        height, width, channels = url_img.shape

        ui_center_x = width / 2 - max_loc3[0]
        ui_center_y = height / 2 - max_loc3[1]

        dif_x = abs(ui_center_x - fi_center_x)
        dif_y = abs(ui_center_y - fi_center_y)

        if dif_x > 5 or dif_y > 5:
            return 0.0
    else:  # for png file
        scale = float(width / (144 - 74))

        height_f, width_f, channels_f = fort_img.shape
        scale_fort = width_f / 320

        url_img = cv2.resize(url_img, None, fx=scale * scale_fort, fy=scale * scale_fort,
                             interpolation=cv2.INTER_NEAREST)

        crop = fort_img[int(74 * scale_fort):int(246 * scale_fort), int(74 * scale_fort):int(144 * scale_fort)]

        if crop.mean() == 255 or crop.mean() == 0:
            return 0.0

        result = cv2.matchTemplate(url_img, crop, cv2.TM_CCOEFF_NORMED)
        min_val3, max_val3, min_loc3, max_loc3 = cv2.minMaxLoc(result)

    return max_val3


def fort_image_matching_imshow(url_img_name, fort_img_name, crop_area = 0):
    url_img_basename = os.path.basename(url_img_name)
    url_img_basename, url_img_ext = os.path.splitext(url_img_basename)

    url_img = cv2.imread(url_img_name, 3)
    fort_img = cv2.imread(fort_img_name, 3)

    if url_img is None or fort_img is None:
        return 0.0

    height, width, channels = url_img.shape

    if url_img_ext == '.jpg':
        if width > height:
            scale = float(288 / height)
        else:
            scale = float(288 / width)

        height_f, width_f, channels_f = fort_img.shape

        scale_fort = width_f / 320

        url_img = cv2.resize(url_img, None, fx=scale * scale_fort, fy=scale * scale_fort,
                             interpolation=cv2.INTER_NEAREST)

        crop_y1 = 74
        crop_y2 = 246
        crop_x1 = 74
        crop_x2 = 144

        if crop_area == 1:
            crop_y1 = 74
            crop_y2 = 174
            crop_x1 = 134
            crop_x2 = 246

        crop = fort_img[int(crop_y1 * scale_fort):int(crop_y2 * scale_fort),
               int(crop_x1 * scale_fort):int(crop_x2 * scale_fort)]

        # Calculate vector from center of fort image(x=74, y=74, width=172, height=172) to top left corner of crop of fort_img
        fi_center_x = (((246 + 74) / 2) * scale_fort) - (crop_x1 * scale_fort)
        fi_center_y = (((246 + 74) / 2) * scale_fort) - (crop_y1 * scale_fort)

        if crop.mean() == 255 or crop.mean() == 0:
            return 0.0

        result = cv2.matchTemplate(url_img, crop, cv2.TM_CCOEFF_NORMED)
        min_val3, max_val3, min_loc3, max_loc3 = cv2.minMaxLoc(result)

        height, width, channels = url_img.shape

        ui_center_x = width / 2 - max_loc3[0]
        ui_center_y = height / 2 - max_loc3[1]

        dif_x = abs(ui_center_x - fi_center_x)
        dif_y = abs(ui_center_y - fi_center_y)

        print(dif_x, dif_y)

        if dif_x > 5 or dif_y > 5:
            return 0.0
    else:  # for png file
        scale = float(width / (144 - 74))

        height_f, width_f, channels_f = fort_img.shape
        scale_fort = width_f / 320

        url_img = cv2.resize(url_img, None, fx=scale * scale_fort, fy=scale * scale_fort,
                             interpolation=cv2.INTER_NEAREST)

        crop = fort_img[int(74 * scale_fort):int(246 * scale_fort), int(74 * scale_fort):int(144 * scale_fort)]

        if crop.mean() == 255 or crop.mean() == 0:
            return 0.0

        result = cv2.matchTemplate(url_img, crop, cv2.TM_CCOEFF_NORMED)
        min_val3, max_val3, min_loc3, max_loc3 = cv2.minMaxLoc(result)

    top_left = max_loc3
    height, width, channels = crop.shape
    bottom_right = (top_left[0] + width, top_left[1] + height)
    cv2.rectangle(url_img, top_left, bottom_right, (0, 255, 0), 2)
    cv2.rectangle(fort_img, (int(crop_x1 * scale_fort), int(crop_y1 * scale_fort)),
                  (int(crop_x2 * scale_fort), int(crop_y2 * scale_fort)), (0, 0, 255), 2)

    cv2.imshow('matching result', url_img)
    cv2.imshow('fort image', fort_img)
    cv2.imshow('crop', crop)
    cv2.waitKey(0)

    if dif_x > 5 or dif_y > 5:
        return 0.0

    return max_val3


def pokemon_image_matching(pokemon_image_name, fort_img_name, is_pokemon):

    pokemon_image = cv2.imread(pokemon_image_name, cv2.IMREAD_UNCHANGED)
    fort_img = cv2.imread(fort_img_name, 3)

    if pokemon_image is None or fort_img is None:
        return 100000.0

    croped = pokemon_image[0:256,0:190]

    height_f, width_f, channels_f = fort_img.shape
    scale = 147 / 256 * width_f / 133

    scaled = cv2.resize(croped, None, fx=scale, fy=scale)

    scaled_h, scaled_w, scaled_c = scaled.shape
    channels = cv2.split(scaled)

    if is_pokemon:
        scale_crop_fort = width_f / 156
        target_x = (16*scale_crop_fort)
        target_y = (28*scale_crop_fort)
        fort_img = fort_img[target_x-2:target_x+2+scaled_h, target_y-2:target_y+2+scaled_w]
    else:
        scale_crop_fort = width_f / 133
        target_x = int(12*scale_crop_fort)
        target_y = int(24*scale_crop_fort)
        fort_img = fort_img[target_x-2:target_x+2+scaled_h, target_y-2:target_y+2+scaled_w]

    scaled_no_alpth = cv2.merge([channels[0], channels[1], channels[2]])
    transparent_mask = cv2.merge([channels[3], channels[3], channels[3]])

    white_pixels = channels[3].sum()/255

    result = cv2.matchTemplate(fort_img, scaled_no_alpth, cv2.TM_SQDIFF, mask=transparent_mask)

    min_val3, max_val3, min_loc3, max_loc3 = cv2.minMaxLoc(result)

    min_val3 = min_val3 / white_pixels

    return min_val3
