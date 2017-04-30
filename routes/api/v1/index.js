const
	express = require('express'),
	bodyParser = require('body-parser'),
	multer = require('multer')({dest:'./uploads'}),
	searchController = require('../../../controllers/api/v1/search'),
	articleController = require('../../../controllers/api/v1/article'),
	userinfoController = require('../../../controllers/api/v1/userinfo');
	useremailController = require('../../../controllers/api/v1/useremail');
	userpasswordController = require('../../../controllers/api/v1/userpassword');

var router = express.Router();

router.get('/search', searchController.index);

router.get('/article', articleController.getArticle);
router.post('/article', multer.array('fulltextfile', 10));
router.post('/article', articleController.putArticle);

router.get('/userinfo', userinfoController.getUserInfo);
router.post('/userinfo', bodyParser.urlencoded({ extended: true }));
router.post('/userinfo', userinfoController.putUserInfo);

router.post('/userpassword', bodyParser.urlencoded({ extended: true }));
router.post('/userpassword', userpasswordController.putUserPassword);

router.get('/useremail', useremailController.getUserEmail);
router.post('/useremail', bodyParser.urlencoded({ extended: true }));
router.post('/useremail', useremailController.putUserEmail);
router.delete('/useremail', bodyParser.urlencoded({ extended: true }));
router.delete('/useremail', useremailController.deleteUserEmail);

module.exports = router;

