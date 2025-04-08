from flask import views, render_template, request, url_for
from flask_cors import cross_origin
import cv2
import numpy as np
import base64
from werkzeug.utils import secure_filename
import os
import uuid
import psycopg2

# import Liveness Code
from FaceLiveness.liveness import get_face_liveness
from Routes.face_utils import Face

from app import app, vec, det


# DB info
from queries import (
    register_user_query,
    search_before_register_query,
    add_transaction_query,
    check_username_query
)
from configuration.db_config import conn
from configuration.config import LIVENESS_THRESHOLD

cur = conn.cursor()

# Image file allowed Extensions
IMAGE_ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']



class Register(views.MethodView):

    @cross_origin()
    def get(self):
        return render_template("register.html")

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

        image_file = request.files.get('image', None)

        username = request.form.get('username', None)

        # SERVICE TYPE ===> LOGIN or REGISTER
        SERVICE_TYPE = "REGISTER"

        # check for image
        if image_file == None:
            return { 'status': 'failed', 'message': "imageFile is required", 'code':7 }, 200

        # check for username
        if username == None or username == "":
            return { 'status': 'failed', 'message': "Username is required", 'code':7 }, 200
        
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
                # username = "UNKNOWN" ===> Got Username from USER Input
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
                # BUT first we need to  REGISTER USER

                # ==== check if username already exists
                cur.execute(check_username_query, (username, companyId))
                result = cur.fetchall()

                if len(result) > 0:
                    # username = "KNOWN" ===> USER INPUT
                    face_image = str(transaction_id) + ".png" # psycopg2.Binary(byte_image)
                    matching_score = 0.0
                    status = "FAIL"
                    reason = 'Username already exist!'
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

                    return { 'status': 'failed', 'message': 'Username already exist, please choose diiferent one!'}


                # ==== check if user's face already exists with other username
                # GET FACE Embeddings using bboxes, kpss
                face = Face(bbox=bboxes[0][:-1], kps=np.array(kpss[0]), det_score=bboxes[0][-1])
                embeddings, aligned_face = vec.get(image, face)

                cur.execute(search_before_register_query, (embeddings.tolist(), companyId))
                result = cur.fetchall()

                

                if len(result) > 0:
                    face_image = str(transaction_id) + ".png" # psycopg2.Binary(byte_image)
                    matching_score = 0.0
                    status = "FAIL"
                    reason = 'Account already exists for this Face!'
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

                    return { 'status': 'failed', 'message': 'Account already exists for this Face, please try Login!', 'associatedVerificationId': result }

                # username = "KNOWN" ===> USER INPUT
                # CREATE User
                face_image = str(transaction_id) + ".png" # psycopg2.Binary(byte_image)

                cur.execute(register_user_query, (username, embeddings.tolist(), face_image, RefID, associatedVerificationId, companyId))
                conn.commit()

                matching_score = 0.0
                status = "SUCCESS"
                reason = 'No Spoof Detected & Registration Successful!'
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

                image_file.stream.seek(0)
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'users', str(transaction_id) + ".png"))
                return {'status': 'success', 'message': 'No Spoof Detected & Registration Successful!', 'code': 1 }, 200
    