import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models



def migrate_legacy_profile_data(apps, schema_editor):
    StudentProfile = apps.get_model('placements','StudentProfile')
    College = apps.get_model('placements','College')
    SkillCatalog = apps.get_model('placements','SkillCatalog')
    Skill = apps.get_model('placements','Skill')
    labels={'java':'Java','c':'C','python':'Python','cplusplus':'C++','javascript':'JavaScript','csharp':'C#','php':'PHP','sql':'SQL','html':'HTML'}
    for profile in StudentProfile.objects.all().iterator():
        if getattr(profile,'college',None) and not profile.college_ref_id:
            college,_=College.objects.get_or_create(name=profile.college.strip())
            profile.college_ref_id=college.pk
            profile.save(update_fields=['college_ref'])
        try: legacy=Skill.objects.get(student_id=profile.pk)
        except Skill.DoesNotExist: legacy=None
        if legacy:
            selected=[]
            for field,label in labels.items():
                if getattr(legacy,field,False):
                    skill,_=SkillCatalog.objects.get_or_create(name=label)
                    selected.append(skill.pk)
            profile.skills_catalog.set(selected)

class Migration(migrations.Migration):
    dependencies=[('placements','0002_placement_architecture'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
      migrations.AddField('studentprofile','skills_catalog',models.ManyToManyField(blank=True,related_name='students',to='placements.skillcatalog')),
      migrations.AddField('studentprofile','resume',models.FileField(blank=True,null=True,upload_to='resumes/%Y/%m/')),
      migrations.AddField('studentprofile','is_active',models.BooleanField(default=True)),
      migrations.AddField('placementdrive','recruiters',models.ManyToManyField(blank=True,related_name='managed_placement_drives',to=settings.AUTH_USER_MODEL)),
      migrations.AddField('placementhistory','company',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='placement_history',to='placements.company')),
      migrations.AddField('placementhistory','placement_drive',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='placement_history',to='placements.placementdrive')),
      migrations.AddField('placementhistory','status',models.CharField(default='PLACED',max_length=20)),
      migrations.AddField('studymaterial','title',models.CharField(default='Study Material',max_length=255)),
      migrations.AddField('studymaterial','description',models.TextField(blank=True)),
      migrations.AddField('studymaterial','category',models.CharField(blank=True,max_length=100)),
      migrations.AddField('studymaterial','file',models.FileField(blank=True,null=True,upload_to='materials/%Y/%m/')),
      migrations.AddField('studymaterial','external_url',models.URLField(blank=True)),
      migrations.AddField('studymaterial','uploaded_by',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='uploaded_materials',to=settings.AUTH_USER_MODEL)),
      migrations.AddField('studymaterial','is_published',models.BooleanField(default=True)),
      migrations.AddField('announcement','audience',models.CharField(choices=[('GLOBAL','Everyone'),('COLLEGE','Selected colleges'),('DRIVE','Placement drive'),('STUDENT','Specific students')],default='GLOBAL',max_length=20)),
      migrations.AddField('announcement','placement_drive',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.CASCADE,related_name='announcements',to='placements.placementdrive')),
      migrations.AddField('announcement','published_at',models.DateTimeField(blank=True,null=True)),
      migrations.AddField('announcement','colleges',models.ManyToManyField(blank=True,related_name='announcements',to='placements.college')),
      migrations.AddField('announcement','students',models.ManyToManyField(blank=True,related_name='targeted_announcements',to='placements.studentprofile')),
      migrations.CreateModel(name='RecruiterProfile',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('phone',models.CharField(blank=True,max_length=20)),('created_at',models.DateTimeField(auto_now_add=True)),('company',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='recruiters',to='placements.company')),('user',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name='recruiter_profile',to=settings.AUTH_USER_MODEL))]),
      migrations.RunPython(migrate_legacy_profile_data, migrations.RunPython.noop),
      migrations.CreateModel(name='Gallery',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('title',models.CharField(max_length=255)),('description',models.TextField(blank=True)),('image',models.ImageField(upload_to='gallery/%Y/%m/')),('year',models.PositiveIntegerField(blank=True,null=True)),('display_order',models.PositiveIntegerField(default=0)),('is_published',models.BooleanField(default=True)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('company',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='gallery_entries',to='placements.company'))],options={'ordering':['display_order','-created_at']}),
    ]
