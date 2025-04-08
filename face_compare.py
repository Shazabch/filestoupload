from flask import views, render_template, request, url_for
from flask_cors import cross_origin
import cv2
import numpy as np
import base64
from werkzeug.utils import secure_filename
import os
import uuid
import psycopg2

from Routes.face_utils import Face, compute_sim, match_score
from app import app, vec, det

# Image file allowed Extensions
IMAGE_ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']

class FaceCompare(views.MethodView):

    @cross_origin()
    def get(self):
        return render_template('face_compare.html')

    @cross_origin()
    def post(self):

        companyId = request.form.get('companyId', None)
        if companyId == None or companyId == "":
            return { 'status': 'failed', 'message': "Company Id is required", 'code':7 }, 200

        associatedVerificationId = request.form.get("associatedVerificationId", None)

        if associatedVerificationId == None or associatedVerificationId == "":
            return { 'status': 'failed', 'message': "Verification Id is required", 'code':7 }, 200

        # Get RefID from URL form
        RefID = request.form.get('RefID', None)
        if RefID == None:
            RefID = 'N/A'
            
        
        image1 = request.files.get('image1', None)
        image2 = request.files.get('image2', None)

        if image1 == None:
            return { 'status': 'failed', 'message': 'Image1 is required!'}, 404

        elif image2 == None:
            return { 'status': 'failed', 'message': 'Image2 is required!'}, 404

        
        # GET Filenames
        try:
            fileExt = image1.filename.split('.')[-1]
            if not fileExt in IMAGE_ALLOWED_EXTENSIONS:
                return { 
                    'status': 'failed',
                    'message': f'{fileExt.upper()} file1 is not supported. Allowed file extensions are {IMAGE_ALLOWED_EXTENSIONS}'
                }

            # READ Image File with CV2
            byte_image1 = image1.read()
            image1 = cv2.imdecode(np.frombuffer(byte_image1, np.uint8), cv2.IMREAD_COLOR)

            # CHECK for FACE
            bboxes1, kpss1 = det.detect(image1)
            bboxes1 = bboxes1.tolist()
            kpss1 = kpss1.tolist()

            if len(bboxes1) > 1:
                return { 'status': 'failed', 'message': 'Multiple faces found in the image', 'code': 4 }, 200

            elif len(bboxes1) == 0:
                return { 'status': 'failed', 'message': 'No face found in the image', 'code':3 }, 200

            else:
                face1 = Face(bbox=bboxes1[0][:-1], kps=np.array(kpss1[0]), det_score=bboxes1[0][-1])
                embeddings1, aligned_face1 = vec.get(image1, face1)
        except:
            return { 'status': 'failed', 'message': 'Image1 file is not valid!'}, 404



        # GET Filenames
        try:
            fileExt = image2.filename.split('.')[-1]
            if not fileExt in IMAGE_ALLOWED_EXTENSIONS:
                return { 
                    'status': 'failed',
                    'message': f'{fileExt.upper()} file2 is not supported. Allowed file extensions are {IMAGE_ALLOWED_EXTENSIONS}'
                }

            # READ Image File with CV2
            byte_image2 = image2.read()
            image2 = cv2.imdecode(np.frombuffer(byte_image2, np.uint8), cv2.IMREAD_COLOR)

            # CHECK for FACE
            bboxes2, kpss2 = det.detect(image2)
            bboxes2 = bboxes2.tolist()
            kpss2 = kpss2.tolist()

            if len(bboxes2) > 1:
                return { 'status': 'failed', 'message': 'Multiple faces found in the image', 'code': 4 }, 200

            elif len(bboxes2) == 0:
                return { 'status': 'failed', 'message': 'No face found in the image', 'code':3 }, 200

            else:
                face2 = Face(bbox=bboxes2[0][:-1], kps=np.array(kpss2[0]), det_score=bboxes2[0][-1])
                embeddings2, aligned_face2 = vec.get(image2, face2)
        except:
            return { 'status': 'failed', 'message': 'Image2 file is not valid!'}, 404


        # Calculate Score
        matching_score = match_score(compute_sim(embeddings1, embeddings2))

        return {
            'status': 'success',
            'message': 'success',
            'score': round(matching_score, 2)
        }
