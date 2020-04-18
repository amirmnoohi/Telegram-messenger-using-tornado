import os
import os.path
from binascii import hexlify

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import torndb
from tornado.options import define, options

define("port", default=1104, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="messenger database host")
define("mysql_database", default="messenger", help="messenger database name")
define("mysql_user", default="root", help="messenger database user")
define("mysql_password", default=":D", help="messenger database password")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            # GET METHOD :
            (r"/signup", Signup),
            (r"/login", Login),
            (r"/logout", Logout),
            (r"/creategroup", Creategroup),
            (r"/createchannel", Createchannel),
            (r"/getuserlist", Getuserlist),
            (r"/getgrouplist", Getgrouplist),
            (r"/getchannellist", Getchannellist),
            (r"/getuserchats", Getuserchats),
            (r"/getgroupchats", Getgroupchats),
            (r"/getchannelchats", Getchannelchats),
            (r"/sendmessageuser", Sendmessageuser),
            (r"/sendmessagegroup", Sendmessagegroup),
            (r"/sendmessagechannel", Sendmessagechannel),
            (r"/joingroup", Joingroup),
            (r"/joinchannel", Joinchannel),
            (r"/getname", Getname),
            (r"/(favicon\.ico)", tornado.web.StaticFileHandler, {'path': ''}),
            (r".*", Defaulthandler),
        ]
        settings = dict()
        super(Application, self).__init__(handlers, **settings)
        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def check_username(self, user):
        resuser = self.db.get("SELECT * from users where username = %s", user)
        if resuser:
            return True
        else:
            return False

    def check_group(self, group):
        resgroup = self.db.get("SELECT * from groups where group_name = %s", group)
        if resgroup:
            return True
        else:
            return False

    def joined_group(self, username, group_name):
        resuser = self.db.get("SELECT * from user_group where user_name = %s and group_name = %s", username, group_name)
        if resuser:
            return True
        else:
            return False

    def joined_channel(self, username, channel_name):
        resuser = self.db.get("SELECT * from user_channel where user_name = %s and channel_name = %s", username,
                              channel_name)
        if resuser:
            return True
        else:
            return False

    def is_admin_group(self, user_name, group_name):
        resuser = self.db.get("SELECT * from groups where creator_username = %s and group_name = %s", user_name,
                              group_name)
        if resuser:
            return True
        else:
            return False

    def is_admin_channel(self, user_name, channel_name):
        resuser = self.db.get("SELECT * from channel where creator_username = %s and channel_name = %s", user_name,
                              channel_name)
        if resuser:
            return True
        else:
            return False

    def check_channel(self, channel):
        reschannel = self.db.get("SELECT * from channel where channel_name = %s", channel)
        if reschannel:
            return True
        else:
            return False

    def check_pass(self, username, password):
        resuser = self.db.get("SELECT * from users where username = %s and password = %s", username, password)
        if resuser:
            return True
        else:
            return False

    def check_loggedin(self, username, password):
        resuser = self.db.get("SELECT * from users where username = %s and password = %s", username, password)
        if resuser['is_active'] == '1':
            return True
        else:
            return False

    def check_date(self, dt):
        for zxc in dt:
            if not zxc.isdigit():
                return False
        return True

    def user_from_token(self, token):
        username = self.db.get("""
                    Select username
                    from users
                    where token = %s
                    """, token)
        if username:
            return username['username']
        else:
            return False


class Defaulthandler(BaseHandler):
    def get(self):
        output = {'POWERED BY': 'AMIR M NOOHI'}
        self.write(output)

    def post(self, *args, **kwargs):
        output = {'POWERED BY': 'AMIR M NOOHI'}
        self.write(output)


class Signup(BaseHandler):
    def get(self, *args, **kwargs):
        if not self.check_username(self.get_argument('username')):
            self.db.execute("""
                            INSERT INTO users (username, password, firstname, lastname,is_active, create_date)
                            values (%s,%s,%s,%s,%s,NOW())
                            """,
                            self.get_argument('username'),
                            self.get_argument('password'),
                            self.get_argument('firstname', default=None),
                            self.get_argument('lastname', default=None),
                            '0')
            output = {'code': '200',
                      'message': 'Signed Up Successfully'}
            self.write(output)
        else:
            output = {'code': '204',
                      'message': 'User Exist Try Another!'}
            self.write(output)


class Login(BaseHandler):
    def get(self, *args, **kwargs):
        if self.check_username(self.get_argument('username')):
            if self.check_pass(self.get_argument('username'), self.get_argument('password')):
                if not self.check_loggedin(self.get_argument('username'), self.get_argument('password')):
                    token = str(hexlify(os.urandom(16)))
                    self.db.execute("""
                                    UPDATE users
                                    SET token = %s , is_active = 1
                                    WHERE username = %s and password = %s
                                    """, token, self.get_argument('username'), self.get_argument('password'))
                    output = {
                        'code': '200',
                        'message': 'Logged in Successfully',
                        'token': token
                    }
                    self.write(output)
                else:
                    output = {'code': '200',
                              'message': 'You are already logged in!'}
                    self.write(output)
            else:
                output = {'code': '401',
                          'message': 'Password is not Correct'}
                self.write(output)
        else:
            output = {'code': '404',
                      'message': 'User Not Found'}
            self.write(output)


class Logout(BaseHandler):
    def get(self, *args, **kwargs):
        if self.check_username(self.get_argument('username')):
            if self.check_pass(self.get_argument('username'), self.get_argument('password')):
                if self.check_loggedin(self.get_argument('username'), self.get_argument('password')):
                    self.db.execute("""
                                    UPDATE users
                                    SET token = %s , is_active = 0
                                    WHERE username = %s and password = %s
                                    """, None, self.get_argument('username'), self.get_argument('password'))
                    output = {
                        'code': '200',
                        'message': 'Logged Out Successfully',
                    }
                    self.write(output)
                else:
                    output = {'code': '200',
                              'message': 'You Have not Logged in Yet!'}
                    self.write(output)
            else:
                output = {'code': '401',
                          'message': 'Password is not Correct'}
                self.write(output)
        else:
            output = {'code': '404',
                      'message': 'User Not Found'}
            self.write(output)


class Creategroup(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if not self.check_group(self.get_argument('group_name')):
                self.db.execute("""
                                  INSERT INTO groups (group_name, title, creator_username, create_date)
                                  values (%s,%s,%s,NOW())
                                """,
                                self.get_argument('group_name'),
                                self.get_argument('group_title', default=None),
                                self.user_from_token(self.get_argument('token')))
                self.db.execute("""
                                    insert into user_group ( user_name, group_name, join_date)
                                    values (%s,%s,NOW())""",
                                self.user_from_token(self.get_argument('token')),
                                self.get_argument('group_name'))
                output = {'code': '200',
                          'message': 'Group Created Successfully'}
                self.write(output)

            else:
                output = {'code': '204',
                          'message': 'Group_name Exist Try Another!'}
                self.write(output)

        else:
            output = {'code': '401',
                      'message': 'token is not Correct'}
            self.write(output)


class Createchannel(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if not self.check_channel(self.get_argument('channel_name')):
                self.db.execute("""
                                  INSERT INTO channel (channel_name, title, creator_username, create_date)
                                  values (%s,%s,%s,NOW())
                                """,
                                self.get_argument('channel_name'),
                                self.get_argument('channel_title', default=None),
                                self.user_from_token(self.get_argument('token')))
                self.db.execute("""
                                    insert into user_channel ( user_name, channel_name, join_date)
                                    values (%s,%s,NOW())""",
                                self.user_from_token(self.get_argument('token')),
                                self.get_argument('channel_name'))
                output = {'code': '200',
                          'message': 'Channel Created Successfully'}
                self.write(output)

            else:
                output = {'code': '204',
                          'message': 'Channel_name Exist Try Another!'}
                self.write(output)

        else:
            output = {'code': '401',
                      'message': 'token is not Correct'}
            self.write(output)


class Getuserlist(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            res = self.db.query("""
                                  select distinct src from(select distinct dst as src
                                                             from message_user_to_user
                                                             where src = %s
                                                             UNION ALL select distinct src from message_user_to_user where dst = %s) as z;
                                """, self.user_from_token(self.get_argument('token')),
                                self.user_from_token(self.get_argument('token')))
            ans = {}
            block_number = 0
            for i in res:
                ans['block ' + str(block_number)] = i
                block_number += 1
            ans['code'] = '200'
            if block_number <= 1:
                ans['message'] = 'You Have Chat With -' + str(block_number) + '- User'
            else:
                ans['message'] = 'You Have Chat With -' + str(block_number) + '- Users'
            self.write(ans)

        else:
            output = {'code': '401',
                      'message': 'token is not Correct'}
            self.write(output)


class Getgrouplist(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            res = self.db.query("""
                                  select distinct group_name
                                  from users inner join user_group 
                                  on (username = user_name)
                                  where username = %s
                                """, self.user_from_token(self.get_argument('token')))
            ans = {}
            block_number = 0
            for i in res:
                ans['block ' + str(block_number)] = i
                block_number += 1
            ans['code'] = '200'
            if block_number <= 1:
                ans['message'] = 'You Are in -' + str(block_number) + '- Group'
            else:
                ans['message'] = 'You Are in -' + str(block_number) + '- Groups'
            self.write(ans)
        else:
            output = {'code': '401',
                      'message': 'token is not Correct'}
            self.write(output)


class Getchannellist(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            res = self.db.query("""
                                  select distinct channel_name
                                  from users inner join user_channel on (user_name = username)
                                  where username = %s
                                """, self.user_from_token(self.get_argument('token')))
            ans = {}
            block_number = 0
            for i in res:
                ans['block ' + str(block_number)] = i
                block_number += 1
            ans['code'] = '200'
            if block_number <= 1:
                ans['message'] = 'You Are in -' + str(block_number) + '- Channel'
            else:
                ans['message'] = 'You Are in -' + str(block_number) + '- Channels'
            self.write(ans)
        else:
            output = {'code': '401',
                      'message': 'token is not Correct'}
            self.write(output)


class Getuserchats(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            src = self.user_from_token(self.get_argument('token'))
            dst = self.get_argument('dst')
            dt = self.get_argument('date', default=20000000000000)
            if len(str(dt)) != 14 or not self.check_date(str(dt)):
                output = {'code': '401',
                          'message': 'Bad Date Format'}
                self.write(output)
            else:
                if dt == 20000000000000:
                    dt = '2000-01-01 00:00:00'
                res = self.db.query("""
                                    select src,dst,body, CAST(message_user_to_user.create_date as char) as 'date'
                                    from message_user_to_user 
                                    where ((src = %s and dst = %s) or (src = %s and dst = %s)) and create_date >= %s
                                    order by date asc 
                                    """,
                                    src,
                                    dst,
                                    dst,
                                    src,
                                    str(dt)
                                    )
                ans = {}
                block_number = 0
                for i in res:
                    ans['block ' + str(block_number)] = i
                    block_number += 1
                ans['code'] = '200'
                if block_number == 1:
                    ans['message'] = 'There Are -' + str(block_number) + '- Message'
                else:
                    ans['message'] = 'There Are -' + str(block_number) + '- Messages'
                self.write(ans)

        else:
            output = {'code': '401',
                      'message': 'token is not Correct'}
            self.write(output)


class Getgroupchats(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.joined_group(self.user_from_token(self.get_argument('token')), self.get_argument('dst')):
                dt = self.get_argument('date', default=20000000000000)
                if len(str(dt)) != 14 or not self.check_date(str(dt)):
                    output = {'code': '401',
                              'message': 'Bad Date Format'}
                    self.write(output)
                else:
                    if dt == 20000000000000:
                        dt = '2000-01-01 00:00:00'
                    res = self.db.query("""
                                        select src,dst,body, CAST(create_date as char) as 'date'
                                        from message_user_to_group 
                                        where dst=%s and create_date >= %s
                                        order by date asc 
                                        """, self.get_argument('dst'), str(dt))
                    ans = {}
                    block_number = 0
                    for i in res:
                        ans['block ' + str(block_number)] = i
                        block_number += 1
                    ans['code'] = '200'
                    if block_number == 1:
                        ans['message'] = 'There Are -' + str(block_number) + '- Message'
                    else:
                        ans['message'] = 'There Are -' + str(block_number) + '- Messages'
                    self.write(ans)

            else:
                output = {'code': '404',
                          'message': 'You are not in This Group'}
                self.write(output)
        else:
            output = {'code': '401',
                      'message': 'token is not Correct'}
            self.write(output)


class Getchannelchats(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.joined_channel(self.user_from_token(self.get_argument('token')), self.get_argument('dst')):
                dt = self.get_argument('date', default=20000000000000)
                if len(str(dt)) != 14 or not self.check_date(str(dt)):
                    output = {'code': '401',
                              'message': 'Bad Date Format'}
                    self.write(output)
                else:
                    if dt == 20000000000000:
                        dt = '2000-01-01 00:00:00'
                    res = self.db.query("""
                                        select src,dst,body, CAST(create_date as char) as 'date'
                                        from message_user_to_channel 
                                        where dst = %s and create_date >= %s
                                        order by date asc 
                                        """, self.get_argument('dst'), str(dt))
                    ans = {}
                    block_number = 0
                    for i in res:
                        ans['block ' + str(block_number)] = i
                        block_number += 1
                    ans['code'] = '200'
                    if block_number == 1:
                        ans['message'] = 'There Are -' + str(block_number) + '- Message'
                    else:
                        ans['message'] = 'There Are -' + str(block_number) + '- Messages'
                    self.write(ans)

            else:
                output = {'code': '404',
                          'message': 'You are not in This Channel'}
                self.write(output)
        else:
            output = {'code': '401',
                      'message': 'token is not Correct'}
            self.write(output)


class Sendmessageuser(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.check_username(self.get_argument('dst')):
                self.db.execute("""
                                    insert into message_user_to_user (src, dst, body, create_date) 
                                    values (%s,%s,%s,NOW())
                                    """,
                                self.user_from_token(self.get_argument('token')),
                                self.get_argument('dst'),
                                self.get_argument('body', default=None)
                                )
            else:
                output = {'code': '404',
                          'message': 'Destination User Not Found'}
                self.write(output)
                return

            output = {'code': '200',
                      'message': 'Message Sent Successfully'}
            self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class Joingroup(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.check_group(self.get_argument('group_name')):
                if not self.joined_group(self.user_from_token(self.get_argument('token')),
                                         self.get_argument('group_name')):
                    self.db.execute("""
                    insert into user_group ( user_name, group_name, join_date)
                    values (%s,%s,NOW())""",
                                    self.user_from_token(self.get_argument('token')),
                                    self.get_argument('group_name'))
                    output = {'code': '200',
                              'message': 'Successfully Joined'}
                    self.write(output)
                else:
                    output = {'code': '200',
                              'message': 'You are already Joined!'}
                    self.write(output)
            else:
                output = {'code': '404',
                          'message': 'Group Not Found'}
                self.write(output)
        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class Joinchannel(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.check_channel(self.get_argument('channel_name')):
                if not self.joined_channel(self.user_from_token(self.get_argument('token')),
                                           self.get_argument('channel_name')):
                    self.db.execute("""
                    insert into user_channel ( user_name, channel_name, join_date)
                    values (%s,%s,NOW())""",
                                    self.user_from_token(self.get_argument('token')),
                                    self.get_argument('channel_name'))
                    output = {'code': '200',
                              'message': 'Successfully Joined'}
                    self.write(output)
                else:
                    output = {'code': '200',
                              'message': 'You are already Joined!'}
                    self.write(output)
            else:
                output = {'code': '404',
                          'message': 'Channel Not Found'}
                self.write(output)
        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class Sendmessagegroup(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.joined_group(self.user_from_token(self.get_argument('token')), self.get_argument('dst')):
                self.db.execute("""
                                    insert into message_user_to_group (src, dst, body, create_date) 
                                    values (%s,%s,%s,NOW())
                                    """,
                                self.user_from_token(self.get_argument('token')),
                                self.get_argument('dst'),
                                self.get_argument('body', default=None)
                                )
                output = {'code': '200',
                          'message': 'Message Sent Successfully'}
                self.write(output)
            else:
                output = {'code': '404',
                          'message': 'You Are not in This Group'}
                self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class Sendmessagechannel(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.joined_channel(self.user_from_token(self.get_argument('token')), self.get_argument('dst')):
                if self.is_admin_channel(self.user_from_token(self.get_argument('token')),
                                         self.get_argument('dst')):
                    self.db.execute("""
                                        insert into message_user_to_channel (src, dst, body, create_date) 
                                        values (%s,%s,%s,NOW())
                                        """,
                                    self.user_from_token(self.get_argument('token')),
                                    self.get_argument('dst'),
                                    self.get_argument('body', default=None)
                                    )
                    output = {'code': '200',
                              'message': 'Message Successfully Sent'}
                    self.write(output)
                else:
                    output = {'code': '404',
                              'message': 'You are not Admin of This Channel'}
                    self.write(output)
            else:
                output = {'code': '404',
                          'message': 'You Are not in This Channel'}
                self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)

class Getname(BaseHandler):
    def get(self, *args, **kwargs):
        if self.check_username(self.get_argument('username')):
            out = self.db.get("""
                            select username , firstname , lastname
                            from users
                            where username = %s 
                               """,self.get_argument('username'))
            output = {
                'code':'200',
                'message' : 'User Was Found'}
            output['username']=out['username']
            output['firstname']=out['firstname']
            output['lastname']=out['lastname']
            self.write(output)

        else:
            output = {'code': '404',
                      'message': 'User Not Found'}
            self.write(output)


class Test(BaseHandler):
    def get(self, *args, **kwargs):
        res = self.db.query("""
                    select username,password,firstname,lastname,is_active,token
                    from users
        """)
        ans = {}
        block_number = 0
        for i in res:
            ans['block ' + str(block_number)] = i
            block_number += 1

        self.write(ans)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
