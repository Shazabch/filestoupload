from flask import views, render_template, request, url_for
from flask_cors import cross_origin
import cv2
import numpy as np
import base64
from werkzeug.utils import secure_filename
import os
import uuid
import psycopg2
import math

# import Liveness Code
from FaceLiveness.liveness import get_face_liveness
from Routes.face_utils import Face, compute_sim, match_score

from app import app, vec, det


# DB info
from queries import (
    search_query,
    add_transaction_query
)
from configuration.db_config import conn
from configuration.config import LIVENESS_THRESHOLD

cur = conn.cursor()

# Image file allowed Extensions
IMAGE_ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']



class Login(views.MethodView):

    @cross_origin()
    def get(self):
        return render_template("login.html")

    @cross_origin()
    def post(self):
        # Get RefID from URL form
        RefID = request.form.get('RefID', None)
        if RefID == None:
            RefID = 'N/A'

        companyId = request.form.get('companyId', None)

        if companyId == None or companyId == "":
            return { 'status': 'failed', 'message': "Company Id is required", 'code':7 }, 200

        associatedVerificationId = request.form.get("associatedVerificationId", None)

        if associatedVerificationId == None or associatedVerificationId == "":
            return { 'status': 'failed', 'message': "Verification Id is required", 'code':7 }, 200

        image_file = request.files.get('image', None)

        # SERVICE TYPE ===> LOGIN or REGISTER
        SERVICE_TYPE = "LOGIN"

        # check for image
        if image_file == None:
            return { 'status': 'failed', 'message': "imageFile is required", 'code':7 }, 200
        

        # Generate a Unique ID
        transaction_id = uuid.uuid1()

        # save file to Transactions Directory
        image_file.stream.seek(0)
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'transactions',  str(transaction_id) + ".png"))


        # Check for File Extensions
        fileExt = image_file.filename.split('.')[-1]
        if not fileExt in IMAGE_ALLOWED_EXTENSIONS:
                return { 
                    'status': 'failed',
                    'message': f'{fileExt.upper()} file is not supported. Allowed file extensions are {IMAGE_ALLOWED_EXTENSIONS}'
                }


        # READ Image File with CV2
        image_file.stream.seek(0)

        # Check for File Extensions
        fileExt = image_file.filename.split('.')[-1]
        if not fileExt in IMAGE_ALLOWED_EXTENSIONS:
                return { 
                    'status': 'failed',
                    'message': f'{fileExt.upper()} file is not supported. Allowed file extensions are {IMAGE_ALLOWED_EXTENSIONS}'
                }


        # READ Image File with CV2
        byte_image = image_file.read()
        image = cv2.imdecode(np.frombuffer(byte_image, np.uint8), cv2.IMREAD_COLOR)

        # CHECK for FACE
        bboxes, kpss = det.detect(image)
        bboxes = bboxes.tolist()
        kpss = kpss.tolist()


        if len(bboxes) > 1:
            return { 'status': 'failed', 'message': 'Multiple faces found in the image', 'code': 4 }, 200

        elif len(bboxes) == 0:
            return { 'status': 'failed', 'message': 'No face found in the image', 'code':3 }, 200

        else:

            live_score = get_face_liveness(image, 0)
            print("Liveness Score: ", live_score)
            if live_score < LIVENESS_THRESHOLD:
                # Add a transaction
                username = "UNKNOWN"
                face_image = str(transaction_id) + ".png" # psycopg2.Binary(byte_image)
                matching_score = 0.0
                status = "FAIL"
                reason = 'Spoof Detected!'
                params = (username, 
                            face_image, 
                            matching_score, 
                            transaction_id, 
                            SERVICE_TYPE,
                            status, 
                            reason,
                            RefID,
                            associatedVerificationId,
                            companyId
                        )
                cur.execute(add_transaction_query, params)
                conn.commit()

                return { 'status': 'failed', 'message': 'Spoof Detected!', 'code': 12 }, 200

            else:
                # Add transaction for the SUCCESS
                # BUT first we need to get USERNAME

                # ==== check if user's username
                # GET FACE Embeddings using bboxes, kpss
                face = Face(bbox=bboxes[0][:-1], kps=np.array(kpss[0]), det_score=bboxes[0][-1])
                embeddings, aligned_face = vec.get(image, face)

                

                cur.execute(search_query, (embeddings.tolist(),))
                result = cur.fetchall()
                # print(result)

                if len(result) == 0:
                    username = "UNKNOWN"
                    face_image = str(transaction_id) + ".png" # psycopg2.Binary(byte_image)
                    matching_score = 0.0
                    status = "FAIL"
                    reason = 'No Spoof Detected but No Account Found for this Face!'
                    params = (username, 
                                face_image, 
                                matching_score, 
                                transaction_id, 
                                SERVICE_TYPE, # type (LOGIN or REGISTER)
                                status, 
                                reason, 
                                RefID,
                                associatedVerificationId,
                                companyId
                            )
                    cur.execute(add_transaction_query, params)
                    conn.commit()
                    return {'status': 'failed', 'message': 'Face detected, No Spoof!', 'code': 1 }, 200

                username = result[0][0]
                face_image = str(transaction_id) + ".png" # psycopg2.Binary(byte_image)
                matching_score = match_score(compute_sim(np.array(result[0][1], dtype=float), embeddings))

                status = "SUCCESS"
                reason = 'No Spoof Detected & Account Found!'
                params = (username, 
                            face_image, 
                            matching_score, 
                            transaction_id, 
                            SERVICE_TYPE, # type (LOGIN or REGISTER)
                            status, 
                            reason, 
                            RefID,
                            associatedVerificationId,
                            companyId
                        )
                cur.execute(add_transaction_query, params)
                conn.commit()
                return {'status': 'success', 'message': f"No Spoof Detected & Account Found as '{username}'", 'code': 1 }, 200
    