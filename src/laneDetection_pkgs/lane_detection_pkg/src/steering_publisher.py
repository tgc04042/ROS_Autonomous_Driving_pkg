#! /usr/bin/env python
import cv2
import numpy as np
import serial
import matplotlib.pyplot as plt
from sensor_msgs.msg import CompressedImage, Image
from std_msgs.msg import Int32
from std_msgs.msg import Float32
import time
import rospy
from cv_bridge import CvBridge
import sys

class LaneDetection:
    # customize these values
    #color
    low_yellow = np.array([0, 100, 30]) 
    high_yellow = np.array([100, 230, 255])
    low_white = np.array([40, 130, 0])
    high_white = np.array([255, 255, 255])
    #birdeye points
    #upper_left, upper_right, lower_left, lower_right
    a = 135
    pts1 = np.float32([[320 - a, 280], [320 + a, 280], [0, 340], [640, 340]]) #for showing
    # pts1 = np.float32([[100, 240], [540, 240], [0, 380], [640, 380]]) #for driving
    pts2 = np.float32([[0, 0], [640, 0], [0, 480], [640, 480]])
    
    def __init__(self):
        print("steering_publisher hello")
        rospy.init_node("steering_node")
        self.cvbridge = CvBridge()
        #go to usb_cam-test.launch and change video number ex) value="/dev/video4"
        self.img_sub = rospy.Subscriber("/image_jpeg/compressed",CompressedImage,self.convertImg)  
        self.steering_pub = rospy.Publisher("/wecar/steer", Float32, queue_size=5)
        rospy.spin()

    def convertImg(self, img):
        #frame = self.imgmsg_to_cv2(img)
        frame = self.cvbridge.compressed_imgmsg_to_cv2(img, "bgr8")
        # frame = self.cvbridge.imgmsg_to_cv2(img, "bgr8")
        frame = cv2.resize(frame, dsize=(640, 480), interpolation=cv2.INTER_AREA)
        bird_eye_image = self.bird_eye(frame) # perspective image
        colored_image = self.color_detect(bird_eye_image) # binary image
        self.slidng_list_left = self.sliding_left(colored_image)
        self.sliding_list_right = self.sliding_right(colored_image)
        #print("left : {}".format(self.slidng_list_left))
        #print("right : {}".format(self.sliding_list_right))
        frame_steer = self.steering(frame, self.slidng_list_left, self.sliding_list_right)
        
        #visualization
        visualization = False
        if visualization == True:
            #1.birdeye points
            arr1 = map(tuple, self.pts1)
            for i, a in enumerate(arr1):
                cv2.circle(frame, a, 5,(255,(i+1)*50,(i+1)*50), -1)
            #2.list points
            for i in self.slidng_list_left:
                cv2.circle(bird_eye_image, i, 5,(255,255,0), -1)
            for i in self.sliding_list_right:
                cv2.circle(bird_eye_image, i, 5,(255,0,255), -1)
            cv2.imshow("frame", frame)
            cv2.imshow("bird_eye_and_colored_image", bird_eye_image)
            cv2.imshow("colored_image", colored_image)
            cv2.waitKey(1)

    def steering(self, frame, slidng_list_left, sliding_list_right):
        x_left = []
        x_right = []
        image_width = 320
        if len(slidng_list_left) == 0:
            left_distance = 0
        else:
            left_distance = image_width - slidng_list_left[0][0] #should be positive
        # print(slidng_list_left)        

        if len(sliding_list_right) == 0:
            right_distance = 0
        else:
            right_distance = image_width - sliding_list_right[0][0] #should be negative
        # print(sliding_list_right)
        #print("left_distance : {}".format(left_distance))
        #print("right_distance : {}".format(right_distance))
        #extract x coordinates from slidng_list_left
        for i in range(0, len(slidng_list_left)): 
            x_left.append(slidng_list_left[i][0])
        #print("x_left = {}".format(x_left))
        
        left_diff_arr = np.diff(x_left)
        divider = len(left_diff_arr)
        if divider == 0:
            divider = 1
        left_diff_sum = np.sum(left_diff_arr)
        left_avg = int(left_diff_sum/divider)
        
        # print("left_diff_arr{}".format(left_diff_arr))
        # print("left_diff_sum{}".format(left_diff_sum))
        #print("left_avg = {}".format(left_avg))

        #remove inappropriate cases 
        for i in range(0, len(left_diff_arr)): 
            if (left_diff_arr[i] > (left_avg +80)) or (left_diff_arr[i] < (left_avg - 80)): #the value 80 can be modified
                self.slidng_list_left = []
                left_diff_sum = 0

        #extract x coordinates from sliding_list_right
        for i in range(0, len(sliding_list_right)): 
            x_right.append(sliding_list_right[i][0])
        right_diff_arr = np.diff(x_right)
        divider = len(right_diff_arr)
        if divider == 0:
            divider = 1
        right_diff_sum = np.sum(right_diff_arr)
        right_avg = int(right_diff_sum/divider)

        #remove inappropriate cases
        for i in range(0, len(right_diff_arr)): 
            if (right_diff_arr[i] > (right_avg +80)) or (right_diff_arr[i] < (right_avg - 80)): #the value 80 can be modified
                self.sliding_list_right = []
                right_diff_sum = 0
        
        #publish average values divided by 100
        dist_th = 160
        if left_distance == 0 and right_distance != 0:
            dist_steer = left_distance - dist_th # turn left
        elif right_distance == 0 and left_distance != 0:
            dist_steer = right_distance + dist_th # turn right 
        elif right_distance == 0 and left_distance == 0:
            dist_steer = 0
        else:
            dist_steer = right_distance + left_distance
        avg_val = float((left_diff_sum + right_diff_sum)/2) *-1
        if avg_val > 100:
            avg_val = 100
        elif avg_val < -100:
            avg_val = -100
        avg_val /= 100
        avg_val *= 15
        avg_out = avg_val * 1.0
        dist_out = -dist_steer * 0.03
        print("avg_val : {}".format(avg_out))
        print("dist_steer : {}".format(dist_out))
        self.steering_pub.publish(avg_out + dist_out) # degree
    
        return frame #return frame is for visualization

    def sliding_left(self, img):
        left_list = []
        '''
        row: starting from y=179 to y=460, moving by 40
        col: starting from x=19 to y=300, moving by 5
        '''
        for j in range(179, img.shape[0] - 20, 40): # row
            j_list = []
            for i in range(19, int(img.shape[1]/2) - 20, 5): # col
                num_sum = np.sum(img[j - 19:j + 21, i - 19:i + 21]) #window size is 40*40
                if num_sum > 100000: #pick (i,j) where its num_sum is over 100000
                    j_list.append(i)
            try:
                len_list = []
                #print("j_list = {}".format(j_list)) 
                #cluster if a gap between elements in the list is over 5
                result = np.split(j_list, np.where(np.diff(j_list) > 5)[0] + 1) 
                #print("result = {}".format(result))
                for k in range(0, len(result)):
                    len_list.append(len(result[k])) #append the lengths of each cluster
                largest_integer = max(len_list)
            
                for l in range(0, len(result)):
                    if len(result[l]) == largest_integer: 
                        avg = int(np.sum(result[l]) / len(result[l])) #average
                        left_list.append((avg, j)) #avg points of left side 
            except:
                continue
        return left_list

    
    def sliding_right(self, img):
        right_list = []
        '''
        row: starting from x=179 pts1 = np.float32([[100, 240], [540, 240], [0, 380], [640, 380]]) #for driving
        pts2 = np.float32([[0, 0], [640, 0], [0, 480], [640, 480]])to y=560, moving by 40
        col: starting from x=320 to y=620, moving by 5
        '''
        for j in range(179, img.shape[0] - 20, 40): 
            j_list = []
            for i in range(int(img.shape[1]/2), img.shape[1] - 20, 5): 
                num_sum = np.sum(img[j - 19:j + 21, i - 19:i + 21]) #window size is 20*20
                if num_sum > 100000: #pick (i,j) where its num_sum is over 100000
                    j_list.append(i)
            try:
                len_list = []
                #cluster if a gap between elements in the list is over 5
                result = np.split(j_list, np.where(np.diff(j_list) > 5)[0] + 1) 
                for k in range(0, len(result)):
                    len_list.append(len(result[k])) #append the lengths of each cluster
                largest_integer = max(len_list)
            
                for l in range(0, len(result)):
                    if len(result[l]) == largest_integer: 
                        avg = int(np.sum(result[l]) / len(result[l])) #average
                        right_list.append((avg, j)) #avg points of left side 
            except:
                continue
        return right_list

    def color_detect(self, img):
        hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)
        # cv2.imshow("hls image", hls)
        # cv2.imshow("h", hls[:, :, 0])
        # cv2.imshow("l", hls[:, :, 1])
        # cv2.imshow("s", hls[:, :, 2])
        mask_white = cv2.inRange(hls, self.low_white, self.high_white)
        mask_yellow = cv2.inRange(hls, self.low_yellow, self.high_yellow)
        #cv2.imshow("yellow", mask_yellow)
        #cv2.imshow("white", mask_white)
        mask = cv2.bitwise_or(mask_white, mask_yellow)
        #cv2.imshow("both", mask_white)

        return mask
        #return mask_white
        #return mask_yellow

    def bird_eye(self, frame):
        #customize these values
        matrix = cv2.getPerspectiveTransform(self.pts1, self.pts2)
        result = cv2.warpPerspective(frame, matrix, (640, 480))
        # cv2.imshow("original", frame)
        # cv2.imshow("BEV image", result)
        # cv2.waitKey(1)
        return result

if __name__ == '__main__':
    a = LaneDetection()
